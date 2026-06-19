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

🗄️ Database Connection Module
Provides an asynchronous database layer wrapping the Motor (AsyncIOMotorClient) driver to manage stateful connections with MongoDB.

🚀 Core Methods
Database.connect_db()

Description: Initializes an asynchronous client pool using the MONGO_URI environment variable and binds the default database configuration pointer.

Database.close_db()

Description: Gracefully tears down the open socket connections in the client pool during application shutdown sequences.

📂 Data Collection Accessors
get_files_collection()

Returns: Target collection pointer for system file documents ("files").

get_folders_collection()

Returns: Target collection pointer for virtual directory directory nodes ("folders").

📦 Drive Service Module
Handles file storage mechanics by utilizing Telegram (via Telethon) as an unlimited cloud storage backend while saving metadata references inside MongoDB.

🚀 Core Methods
upload_file(...)
Description: Uploads a raw binary byte stream directly to the user's personal Telegram chat ('me') as an uncompressed document asset, then indexes the generated telegram_message_id into MongoDB.

Returns: JSON metadata dict containing the file's dynamic resource link profile.

download_file_bytes(...)
Description: Connects via Telethon, targets the precise Telegram message ID stored within the database metadata schema, and streams down the raw byte package.

Returns: Tuple format (file_bytes, filename, mime_type).

delete_file(...)
Description: Drops the corresponding metadata asset index row inside MongoDB using an ownership filter guard. (Note: Does not wipe history messages out of the physical Telegram cloud channel).

delete_folder_recursive(...)
Description: Executes a nested depth-first tree traversal down a targeted directory virtual node. It strips out all inner files and nested sub-folder indexes sequentially to avoid data orphaning.