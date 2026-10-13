--[[{
    "name": "Overwriting an entire FlowFile document with new parts"
}]]

function handler(ffdocument, session)

    -- Overwrite FlowFile with a single text content part
    ffdocument:overwrite(function(action)
            action:addContent("Hello world")
        end)

end