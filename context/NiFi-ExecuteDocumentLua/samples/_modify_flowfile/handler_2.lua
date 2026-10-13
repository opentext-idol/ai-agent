--[[{
    "name": "Converting a filename part into an embedded file part"
}]]

function handler(ffdocument, session)

    ffdocument:modify({
        onContentFilename = function(action)
            action:transferFilenameToFile()
        end})

end