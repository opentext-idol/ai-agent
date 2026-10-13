--[[{
    "name": "Calculating hash of each file in a FlowFile document"
}]]

function handler(ffdocument, session)

    local hashFieldFromInputStream = function(inputstream, xmlmetadata)
        local hash = hash_file(
            function()
                return inputstream:read(4096)
            end,
            "MD5")
        xmlmetadata:addChild("MD5HASH"):setValue(hash)
    end

    ffdocument:append({
        onContentFile = function(action)
            action:readFile(
                function(inputstream)
                    hashFieldFromInputStream(inputstream, action:getPartXmlMetadata())
                end)
        end,
        onContentFilename = function(action)
            local inputstream = new LuaInputStream(action:getFilename())
            hashFieldFromInputStream(inputstream, action:getPartXmlMetadata())
        end})

end