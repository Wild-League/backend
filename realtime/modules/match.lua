local nk = require("nakama")

local M = {
  cards = {},
	towers = {}
}

local MatchEvents = {
	-- CARD RELATED EVENTS
	-- send x, y and card_id
	card_spawn = 0,
	-- send x, y and card_id
	card_position = 1,
	-- send card_id and action (attack, walk, death ...)
	card_action = 2,
	-- send card_id (remove the card from the game)
	card_dead = 3,
	-- send card_id and damage (this is for the card receiving the damage)
	card_damage = 4,
	-- send card_id and healing (this is for the card receiving the healing)
	card_healing = 5,

	-- TOWER RELATED EVENTS
	-- tower_id and damage
	tower_damage = 6,
	-- tower_id and healing
	tower_healing = 7,
	-- (tower_id) the tower being destroyed
	tower_destroy = 8
}

-- local function get_enemy_id(presences, user_id)
-- 	for _, id in pairs(presences) do
-- 		if id ~= user_id then return id end
-- 	end
-- end

function M.match_init(context, setupstate)
  nk.logger_info("------------------- Match init")

  local gamestate = {
    presences = setupstate.presences
  }

  local tickrate = 1 -- per sec
  local label = "First Game ever!"

  return gamestate, tickrate, label
end

function M.match_join_attempt(context, dispatcher, tick, state, presence, metadata)
  nk.logger_info("------------------- Match Join Attempt")

  local acceptuser = true
  return state, acceptuser
end

function M.match_join(context, dispatcher, tick, state, presences)
  nk.logger_info("------------------- Match Join")

  for _, presence in ipairs(presences) do
    state.presences[presence.session_id] = presence
  end

  return state
end

function M.match_leave(context, dispatcher, tick, state, presences)
  nk.logger_info("------------------- Match Leave")

  for _, presence in ipairs(presences) do
    state.presences[presence.session_id] = nil
  end

  return state
end

function M.match_loop(context, dispatcher, tick, state, messages)
  nk.logger_info("------------------- Match Loop")

	print('messages', nk.json_encode(messages))

	for _, message in pairs(messages) do
		local opcode = message.op_code
		local user_id = message.sender.user_id

		print('opcode', opcode)

		if not M.cards[user_id] then M.cards[user_id] = {} end
		if not M.towers[user_id] then M.towers[user_id] = {} end

		local data = nk.json_decode(message.data)

		if opcode == MatchEvents.card_spawn then
			local card = {
				x = data.x,
				y = data.y,
				card_name = data.card_name,
				card_id = data.card_id,
				action = data.action,
				opcode = opcode
			}

			M.cards[user_id][data.card_id] = card

			dispatcher.broadcast_message(opcode, nk.json_encode(card), nil, message.sender)
		end

		if opcode == MatchEvents.card_action then
			local card = M.cards[user_id][data.card_id]

			if card then
				card.action = data.action
				dispatcher.broadcast_message(opcode, nk.json_encode({
					card_id = data.card_id,
					action = data.action,
					opcode = opcode
				}), nil, message.sender)
			end
		end

		if opcode == MatchEvents.card_dead then
			local card = M.cards[user_id][data.card_id]

			if card then
				M.cards[user_id][data.card_id] = nil

				dispatcher.broadcast_message(opcode, nk.json_encode({
					card_id = data.card_id,
					opcode = opcode
				}), nil, message.sender)
			end
		end
	end

  return state
end

function M.match_terminate(context, dispatcher, tick, state, grace_seconds)
  nk.logger_info("------------------- Match Terminate")

  local message = "Server shutting down in " .. grace_seconds .. " seconds"
  dispatcher.broadcast_message(2, message)

  return nil
end

function M.match_signal(context, dispatcher, tick, state, data)
  return state, "signal received: " .. data
end

return M
