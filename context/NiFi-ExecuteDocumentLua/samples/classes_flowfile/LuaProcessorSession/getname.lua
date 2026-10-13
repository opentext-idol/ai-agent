--[[{
    "name": "Getting the name of the processor"
}]]

function handler(ffdocument, session)

    local processorName = session:getName()

    log_info(processorName)

end