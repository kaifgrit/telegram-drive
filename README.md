Drive API Module (/api/drive)
Provides a secure virtual file system workspace supporting nested directories, file streaming, and recursive cascade deletions.

🚀 Endpoints
POST /upload

Payload: multipart/form-data (file, phone_number, parent_folder_id optional)

Description: Uploads a file asset to a specified root or sub-folder level.

POST /folder/create

Payload: JSON Body (FolderCreateRequest)

Description: Injects a new folder structural node into the ledger database.

GET /explorer/nodes

Query Params: phone_number, parent_folder_id (optional)

Description: Returns all files and subfolders sharing the targeted partition level.

GET /download/{file_id}

Query Params: phone_number

Description: Streams the requested asset back to the client via chunked binary transfer.

DELETE /file/{file_id}

Query Params: phone_number

Description: Permanently drops the targeted file reference.

DELETE /folder/{folder_id}

Query Params: phone_number

Description: Triggers a recursive cascade deletion of the directory and all nested contents.

Authentication API Module (/api/auth)
Manages client-side worker registration and active Telegram session hooks on the hosting server.

🚀 Endpoints
POST /check-session

Payload: JSON Body (PhoneRequest)

Description: Verifies if a valid .session file physically exists on the disk layout.

POST /send-code

Payload: JSON Body (PhoneRequest)

Description: Requests a verification OTP signature sequence from Telegram's infrastructure.

POST /verify-code

Payload: JSON Body (VerifyRequest)

Description: Validates the OTP token payload to initialize a persistent session connection.