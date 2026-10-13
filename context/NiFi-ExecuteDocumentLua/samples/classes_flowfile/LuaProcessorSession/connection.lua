--[[{
    "name": "Testing whether a connection exists and has available space"
}]]

-- BEGIN COPYRIGHT NOTICE
-- Copyright 2026 Open Text.
--
-- The only warranties for products and services of Open Text and its affiliates and licensors
-- ("Open Text") are as may be set forth in the express warranty statements accompanying such
-- products and services. Nothing herein should be construed as constituting an additional warranty.
-- Open Text shall not be liable for technical or editorial errors or omissions contained herein.
-- The information contained herein is subject to change without notice.
--
-- END COPYRIGHT NOTICE

function handler(ffdocument, session)

    if session:hasConnection("session") then
        log_info("Relationship session is connected")
        
        if session:relationshipAvailable("session") then
            log_info("Relationship session has available space")
        end
    end

end