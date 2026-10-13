--[[{
    "name": "Testing whether a connection exists and has available space"
}]]

function handler(ffdocument, session)

    if session:hasConnection("session") then
        log_info("Relationship session is connected")
        
        if session:relationshipAvailable("session") then
            log_info("Relationship session has available space")
        end
    end

end