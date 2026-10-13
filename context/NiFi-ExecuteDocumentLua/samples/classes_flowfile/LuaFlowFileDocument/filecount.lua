--[[{
    "name": "Counting file or filename parts in a FlowFile"
}]]

function handler(ffdocument, session)

    -- Number of binary files embedded in the FlowFile
    local filePartCount = ffdocument:getFileCount()
    
    -- Number of local file references in the FlowFile
    local filenamePartCount = ffdocument:getFilenameCount()

end