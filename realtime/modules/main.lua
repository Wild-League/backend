local nk = require("nakama")

local function matchmaker_matched(context, matched_users)
	local matched_users_ids = {}

	for _, user in pairs(matched_users) do
		table.insert(matched_users_ids, user.presence.user_id)
	end

	return nk.match_create("match", { presences = matched_users_ids })
end

nk.register_matchmaker_matched(matchmaker_matched)
