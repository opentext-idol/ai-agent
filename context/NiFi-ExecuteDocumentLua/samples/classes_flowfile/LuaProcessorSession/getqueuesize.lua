--[[{
    "name": "Getting the size of the processor input queue"
}]]

function handler(ffdocument, session)

    local queueSize = session:getQueueSize()

    log_info("QueueSize:", queueSize)

end