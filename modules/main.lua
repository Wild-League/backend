local nk = require("nakama")

local function matchmaker_matched(context, matched_users)
	local matched_users_ids = {}

	for _, user in pairs(matched_users) do
		table.insert(matched_users_ids, user.presence.user_id)
	end

	nk.logger_info("matchmaker_matched: " .. #matched_users_ids .. " players")

	local ok, result = pcall(nk.match_create, "match", { presences = matched_users_ids })
	if not ok then
		nk.logger_error("nk.match_create error: " .. tostring(result))
		return nil
	end

	if not result then
		nk.logger_error("nk.match_create returned nil")
		return nil
	end

	nk.logger_info("authoritative match created: " .. tostring(result))
	return result
end

nk.register_matchmaker_matched(matchmaker_matched)
