--[[{
    "name": "Replacing strings in the content text parts"
}]]

function handler(ffdocument, session)

    ffdocument:modify({
        onContent = function(action)
            action:transformContent(
                function(inputstream, outputstream)
                    local pageContent = inputstream:read("a")
                    local normalizedSpaces = pageContent:gsub("%s+", " ")
                    outputstream:write(normalizedSpaces)
                end)
        end})

end