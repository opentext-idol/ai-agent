--[[{
    "name": "Appending new parts to a FlowFile document"
}]]

function handler(ffdocument, session)

    -- Adds a content part and appends replacement XML metadata
    ffdocument:append(function(action)
            action:addContent("Hello world")
            action:getXmlMetadata():addChild("said_hello"):setValue("true")
        end)

end