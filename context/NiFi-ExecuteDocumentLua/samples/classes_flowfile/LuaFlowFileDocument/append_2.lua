--[[{
    "name": "Appending new parts to replace existing parts in a FlowFile document"
}]]

function handler(ffdocument, session)

    ffdocument:append({
        -- preAction = function(action) do_nothing end,
        -- onContent = function(action) do_nothing end,
        onContentFile = function(action)
            action:writeFile(function(outputstream)
                    outputstream:write("This file content has been overwritten")
                end)
        end,
        
        onContentFilename = function(action)
            action:deletePart()
        end
        --, postAction = function(action) do_nothing end
        })

end