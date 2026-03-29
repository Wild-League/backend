local nk = require("nakama")

local M = {}

local MatchEvents = {
	spawn_intent = 20,
	command_intent = 21,
	state_snapshot = 30,
	entity_spawned = 31,
	entity_updated = 32,
	entity_removed = 33,
	damage_event = 34,
	tower_event = 35,
	match_end = 36,
	reject_intent = 37
}

-- Must match tickrate returned from match_init.
local TICKRATE = 10

-- Cached rows from public.card (see ensure_nakama_card_fdw management command).
local card_def_cache = {}

local function cooldown_ticks_from_seconds(seconds)
	local s = tonumber(seconds)
	if not s or s <= 0 then
		return TICKRATE
	end
	return math.max(1, math.floor(s * TICKRATE + 0.5))
end

-- Load combat stats for a card name from PostgreSQL (wildleague.card via FDW in nakama DB).
local function load_card_def(card_name)
	if card_def_cache[card_name] then
		return card_def_cache[card_name]
	end

	local query = [[
		SELECT life, speed, damage, attack_range, cooldown, frame_width, frame_height
		FROM card
		WHERE name = $1
		LIMIT 1
	]]

	local ok, rows = pcall(nk.sql_query, query, { card_name })
	if not ok then
		nk.logger_error("card sql_query failed: " .. tostring(rows))
		return nil
	end
	if not rows or #rows == 0 then
		return nil
	end

	local row = rows[1]
	local life = tonumber(row.life)
	if not life or life <= 0 then
		return nil
	end

	local def = {
		life = life,
		speed = tonumber(row.speed) or 1.0,
		damage = tonumber(row.damage) or 0,
		attack_range = tonumber(row.attack_range) or 0,
		attack_cooldown_ticks = cooldown_ticks_from_seconds(row.cooldown),
		cooldown_ticks = cooldown_ticks_from_seconds(row.cooldown),
		frame_w = tonumber(row.frame_width) or 60,
		frame_h = tonumber(row.frame_height) or 60
	}

	card_def_cache[card_name] = def
	return def
end

local WORLD = {
	min_x = 0,
	max_x = 1344,
	min_y = 0,
	max_y = 756
}

local function sorted_keys(t)
	local keys = {}
	for k, _ in pairs(t) do
		keys[#keys + 1] = k
	end
	table.sort(keys)
	return keys
end

local function clamp(n, lo, hi)
	if n < lo then return lo end
	if n > hi then return hi end
	return n
end

local function dist(x1, y1, x2, y2)
	local dx = x2 - x1
	local dy = y2 - y1
	return math.sqrt(dx * dx + dy * dy), dx, dy
end

-- World X is authoritative (left base west, right base east). Clients always use
-- "viewer" X (local player's side drawn on the right). Left-side players see mirrored X.
local function viewer_to_world_x(x, side)
	if side == "left" then
		return WORLD.max_x - x
	end
	return x
end

local function world_to_viewer_x(x, side)
	if side == "left" then
		return WORLD.max_x - x
	end
	return x
end

local function presences_by_side(state)
	local left, right = {}, {}
	for _, presence in pairs(state.presences) do
		local player = state.players[presence.user_id]
		if player and player.side == "left" then
			left[#left + 1] = presence
		elseif player and player.side == "right" then
			right[#right + 1] = presence
		end
	end
	return left, right
end

local function card_payload(card, viewer_side)
	return {
		entity_id = card.entity_id,
		entity_version = card.entity_version,
		owner_id = card.owner_id,
		card_name = card.card_name,
		x = world_to_viewer_x(card.x, viewer_side),
		y = card.y,
		action = card.action,
		current_life = card.current_life,
		max_life = card.max_life
	}
end

local function tower_payload(tower, viewer_side)
	return {
		tower_id = tower.tower_id,
		owner_id = tower.owner_id,
		x = world_to_viewer_x(tower.x, viewer_side),
		y = tower.y,
		current_life = tower.current_life,
		max_life = tower.max_life,
		destroyed = tower.destroyed
	}
end

local function setup_players_and_towers(state, setupstate)
	local player_order = {}
	for _, user_id in ipairs(setupstate.presences or {}) do
		player_order[#player_order + 1] = user_id
	end

	for index, user_id in ipairs(player_order) do
		local side = index == 1 and "left" or "right"
		state.players[user_id] = {
			user_id = user_id,
			side = side,
			session_count = 0,
			cooldowns = {}
		}

		local tower_x = side == "left" and 202 or 1142
		local t1 = user_id .. "_tower_top"
		local t2 = user_id .. "_tower_bottom"
		state.towers[t1] = {
			tower_id = t1,
			owner_id = user_id,
			x = tower_x,
			y = 198,
			max_life = 100,
			current_life = 100,
			destroyed = false
		}
		state.towers[t2] = {
			tower_id = t2,
			owner_id = user_id,
			x = tower_x,
			y = 578,
			max_life = 100,
			current_life = 100,
			destroyed = false
		}
	end
end

local function broadcast_snapshot(dispatcher, state)
	local left_presences, right_presences = presences_by_side(state)

	local function send_snapshot(viewer_side, presences)
		if #presences == 0 then
			return
		end
		local cards = {}
		for _, entity_id in ipairs(sorted_keys(state.cards)) do
			cards[#cards + 1] = card_payload(state.cards[entity_id], viewer_side)
		end

		local towers = {}
		for _, tower_id in ipairs(sorted_keys(state.towers)) do
			towers[#towers + 1] = tower_payload(state.towers[tower_id], viewer_side)
		end

		dispatcher.broadcast_message(MatchEvents.state_snapshot, nk.json_encode({
			match_tick = state.tick,
			cards = cards,
			towers = towers,
			winner_id = state.winner_id
		}), presences)
	end

	send_snapshot("left", left_presences)
	send_snapshot("right", right_presences)
end

local function reject_intent(dispatcher, message, reason, data)
	dispatcher.broadcast_message(MatchEvents.reject_intent, nk.json_encode({
		reason = reason,
		client_intent_id = data and data.client_intent_id,
		card_id = data and data.card_id
	}), { message.sender })
end

local function maybe_end_match(dispatcher, state)
	if state.winner_id then
		return
	end

	local alive_by_owner = {}
	for user_id, _ in pairs(state.players) do
		alive_by_owner[user_id] = 0
	end

	for _, tower in pairs(state.towers) do
		if not tower.destroyed then
			alive_by_owner[tower.owner_id] = (alive_by_owner[tower.owner_id] or 0) + 1
		end
	end

	local alive_players = {}
	for user_id, alive_count in pairs(alive_by_owner) do
		if alive_count > 0 then
			alive_players[#alive_players + 1] = user_id
		end
	end

	if #alive_players == 1 then
		state.winner_id = alive_players[1]
		dispatcher.broadcast_message(MatchEvents.match_end, nk.json_encode({
			match_tick = state.tick,
			winner_id = state.winner_id
		}))
	end
end

local function process_spawn_intent(dispatcher, state, tick, message, data)
	local owner_id = message.sender.user_id
	local owner = state.players[owner_id]
	if not owner then
		reject_intent(dispatcher, message, "unknown_player", data)
		return
	end

	local card_name = data and data.card_name
	local def = card_name and load_card_def(card_name)
	if not def then
		reject_intent(dispatcher, message, "invalid_card_name", data)
		return
	end

	local card_id = data.card_id
	if type(card_id) ~= "string" or card_id == "" then
		reject_intent(dispatcher, message, "invalid_card_id", data)
		return
	end

	if state.cards[card_id] then
		reject_intent(dispatcher, message, "duplicate_card_id", data)
		return
	end

	local cooldown_until = owner.cooldowns[card_name] or 0
	if tick < cooldown_until then
		reject_intent(dispatcher, message, "card_on_cooldown", data)
		return
	end

	local vx = tonumber(data.x) or WORLD.min_x
	local vy = tonumber(data.y) or WORLD.min_y
	local x = clamp(viewer_to_world_x(vx, owner.side), WORLD.min_x, WORLD.max_x)
	local y = clamp(vy, WORLD.min_y, WORLD.max_y)
	local direction = owner.side == "left" and 1 or -1

	local card = {
		entity_id = card_id,
		entity_version = 1,
		owner_id = owner_id,
		card_name = card_name,
		x = x,
		y = y,
		action = "walk",
		current_life = def.life,
		max_life = def.life,
		speed = def.speed,
		damage = def.damage,
		attack_range = def.attack_range,
		attack_cooldown_ticks = def.attack_cooldown_ticks,
		next_attack_tick = tick + def.attack_cooldown_ticks,
		direction = direction
	}

	state.cards[card_id] = card
	owner.cooldowns[card_name] = tick + def.cooldown_ticks

	local left_presences, right_presences = presences_by_side(state)
	local function send_spawn(viewer_side, presences)
		if #presences == 0 then
			return
		end
		dispatcher.broadcast_message(MatchEvents.entity_spawned, nk.json_encode({
			match_tick = tick,
			client_intent_id = data.client_intent_id,
			entity = card_payload(card, viewer_side)
		}), presences)
	end
	send_spawn("left", left_presences)
	send_spawn("right", right_presences)
end

local function process_messages(dispatcher, state, tick, messages)
	for _, message in pairs(messages) do
		local opcode = tonumber(message.op_code)
		local payload = message.data or "{}"
		if type(payload) ~= "string" then
			payload = nk.json_encode(payload)
		end
		local ok, data = pcall(nk.json_decode, payload)
		if not ok then
			data = {}
		end

		if opcode == MatchEvents.spawn_intent then
			process_spawn_intent(dispatcher, state, tick, message, data)
		end
	end
end

local function emit_entity_updated(dispatcher, state, tick, card)
	local left_presences, right_presences = presences_by_side(state)
	local function send_update(viewer_side, presences)
		if #presences == 0 then
			return
		end
		dispatcher.broadcast_message(MatchEvents.entity_updated, nk.json_encode({
			match_tick = tick,
			entity_id = card.entity_id,
			entity_version = card.entity_version,
			owner_id = card.owner_id,
			card_name = card.card_name,
			x = world_to_viewer_x(card.x, viewer_side),
			y = card.y,
			action = card.action,
			current_life = card.current_life,
			max_life = card.max_life
		}), presences)
	end
	send_update("left", left_presences)
	send_update("right", right_presences)
end

local function get_nearest_enemy_card(state, card)
	local best = nil
	local best_d = math.huge

	for _, entity_id in ipairs(sorted_keys(state.cards)) do
		local other = state.cards[entity_id]
		if other.owner_id ~= card.owner_id then
			local d = dist(card.x, card.y, other.x, other.y)
			if d < best_d then
				best_d = d
				best = other
			end
		end
	end

	return best, best_d
end

local function get_nearest_enemy_tower(state, card)
	local best = nil
	local best_d = math.huge
	for _, tower_id in ipairs(sorted_keys(state.towers)) do
		local tower = state.towers[tower_id]
		if tower.owner_id ~= card.owner_id and not tower.destroyed then
			local d = dist(card.x, card.y, tower.x, tower.y)
			if d < best_d then
				best_d = d
				best = tower
			end
		end
	end
	return best, best_d
end

local function move_towards(card, tx, ty)
	local d, dx, dy = dist(card.x, card.y, tx, ty)
	if d <= 0.0001 then
		return false
	end

	local nx = dx / d
	local ny = dy / d
	local old_x, old_y = card.x, card.y
	card.x = clamp(card.x + nx * card.speed, WORLD.min_x, WORLD.max_x)
	card.y = clamp(card.y + ny * card.speed, WORLD.min_y, WORLD.max_y)
	return old_x ~= card.x or old_y ~= card.y
end

local function simulate(dispatcher, state, tick)
	local removed = {}

	for _, entity_id in ipairs(sorted_keys(state.cards)) do
		local card = state.cards[entity_id]
		local changed = false

		local enemy_card, enemy_distance = get_nearest_enemy_card(state, card)
		if enemy_card then
			if enemy_distance <= card.attack_range then
				if card.action ~= "attack" then
					card.action = "attack"
					changed = true
				end

				if tick >= card.next_attack_tick then
					card.next_attack_tick = tick + card.attack_cooldown_ticks
					enemy_card.current_life = enemy_card.current_life - card.damage
					enemy_card.entity_version = enemy_card.entity_version + 1
					emit_entity_updated(dispatcher, state, tick, enemy_card)

					dispatcher.broadcast_message(MatchEvents.damage_event, nk.json_encode({
						match_tick = tick,
						source_entity_id = card.entity_id,
						target_entity_id = enemy_card.entity_id,
						damage = card.damage,
						target_current_life = enemy_card.current_life
					}))
				end
			else
				if card.action ~= "walk" then
					card.action = "walk"
					changed = true
				end
				if move_towards(card, enemy_card.x, enemy_card.y) then
					changed = true
				end
			end
		else
			local enemy_tower, tower_distance = get_nearest_enemy_tower(state, card)
			if enemy_tower then
				if tower_distance <= card.attack_range then
					if card.action ~= "attack" then
						card.action = "attack"
						changed = true
					end

					if tick >= card.next_attack_tick then
						card.next_attack_tick = tick + card.attack_cooldown_ticks
						enemy_tower.current_life = enemy_tower.current_life - card.damage
						if enemy_tower.current_life <= 0 and not enemy_tower.destroyed then
							enemy_tower.current_life = 0
							enemy_tower.destroyed = true
						end

						dispatcher.broadcast_message(MatchEvents.tower_event, nk.json_encode({
							match_tick = tick,
							tower_id = enemy_tower.tower_id,
							current_life = enemy_tower.current_life,
							destroyed = enemy_tower.destroyed
						}))
					end
				else
					if card.action ~= "walk" then
						card.action = "walk"
						changed = true
					end
					if move_towards(card, enemy_tower.x, enemy_tower.y) then
						changed = true
					end
				end
			end
		end

		if card.current_life <= 0 then
			removed[#removed + 1] = card.entity_id
		elseif changed then
			card.entity_version = card.entity_version + 1
			emit_entity_updated(dispatcher, state, tick, card)
		end
	end

	for _, entity_id in ipairs(removed) do
		local card = state.cards[entity_id]
		if card then
			state.cards[entity_id] = nil
			dispatcher.broadcast_message(MatchEvents.entity_removed, nk.json_encode({
				match_tick = tick,
				entity_id = entity_id,
				owner_id = card.owner_id
			}))
		end
	end

	maybe_end_match(dispatcher, state)
end

function M.match_init(context, setupstate)
	local gamestate = {
		presences = {},
		players = {},
		cards = {},
		towers = {},
		tick = 0,
		winner_id = nil
	}

	setup_players_and_towers(gamestate, setupstate or {})

	local tickrate = 10
	local label = "wildleague_authoritative"
	return gamestate, tickrate, label
end

function M.match_join_attempt(context, dispatcher, tick, state, presence, metadata)
	return state, true
end

function M.match_join(context, dispatcher, tick, state, presences)
	for _, presence in ipairs(presences) do
		state.presences[presence.session_id] = presence
		local player = state.players[presence.user_id]
		if player then
			player.session_count = (player.session_count or 0) + 1
		end
	end

	broadcast_snapshot(dispatcher, state)
	return state
end

function M.match_leave(context, dispatcher, tick, state, presences)
	for _, presence in ipairs(presences) do
		state.presences[presence.session_id] = nil
		local player = state.players[presence.user_id]
		if player then
			player.session_count = math.max(0, (player.session_count or 1) - 1)
		end
	end

	local connected = {}
	for user_id, player in pairs(state.players) do
		if (player.session_count or 0) > 0 then
			connected[#connected + 1] = user_id
		end
	end

	if #connected == 1 and not state.winner_id then
		state.winner_id = connected[1]
		dispatcher.broadcast_message(MatchEvents.match_end, nk.json_encode({
			match_tick = state.tick,
			winner_id = state.winner_id
		}))
	end

	return state
end

function M.match_loop(context, dispatcher, tick, state, messages)
	state.tick = tick
	process_messages(dispatcher, state, tick, messages)
	simulate(dispatcher, state, tick)
	broadcast_snapshot(dispatcher, state)
	return state
end

function M.match_terminate(context, dispatcher, tick, state, grace_seconds)
	dispatcher.broadcast_message(MatchEvents.match_end, nk.json_encode({
		match_tick = state.tick,
		winner_id = state.winner_id
	}))
	return nil
end

function M.match_signal(context, dispatcher, tick, state, data)
	return state, "signal received: " .. data
end

return M
