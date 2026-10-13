--[[{
    "name": "Reading parts in a FlowFile document"
}]]

function handler(ffdocument, session)

    local hashes = {}
    ffdocument:read({
        -- preAction = function(action) do_nothing end,
        onContent = function(action)
            action:readContent(function(inputstream)
                    local pageContent = inputstream:read("a")
                    hashes:insert(hash_string(pageContent))
                end)
        end,
        
        onContentFile = function(action)
            action:readFile(function(inputstream)
                    local fileContent = inputstream:read("a")
                    hashes:insert(hash_string(fileContent))
                end)
        end,
        
        onContentFilename = function(action)
            local f = assert(io.open(action:getFilename()))
            local fileContent = f:read("a")
            f:close()
            hashes:insert(hash_string(fileContent))
        end
        --, postAction = function(action) do_nothing end
        })

end