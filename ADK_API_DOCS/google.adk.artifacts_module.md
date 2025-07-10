### google.adk.artifacts module

**google.adk.artifacts module**

**class** google.adk.artifacts.**BaseArtifactService**  
Bases: ABC

Abstract base class for artifact services.

**abstractmethod async delete\_artifact(\*, app\_name, user\_id, session\_id, filename)**  
Deletes an artifact.

RETURN TYPE:  
None

PARAMETERS:

* **app\_name** – The name of the application.  
* **user\_id** – The ID of the user.  
* **session\_id** – The ID of the session.  
* **filename** – The name of the artifact file.

**abstractmethod async list\_artifact\_keys(\*, app\_name, user\_id, session\_id)**  
Lists all the artifact filenames within a session.

RETURN TYPE:  
list\[str\]

PARAMETERS:

* **app\_name** – The name of the application.  
* **user\_id** – The ID of the user.  
* **session\_id** – The ID of the session.

RETURNS:  
A list of all artifact filenames within a session.

**abstractmethod async list\_versions(\*, app\_name, user\_id, session\_id, filename)**  
Lists all versions of an artifact.

RETURN TYPE:  
list\[int\]

PARAMETERS:

* **app\_name** – The name of the application.  
* **user\_id** – The ID of the user.  
* **session\_id** – The ID of the session.  
* **filename** – The name of the artifact file.

RETURNS:  
A list of all available versions of the artifact.

**abstractmethod async load\_artifact(\*, app\_name, user\_id, session\_id, filename, version=None)**  
Gets an artifact from the artifact service storage.

The artifact is a file identified by the app name, user ID, session ID, and filename.

RETURN TYPE:  
Optional\[Part\]

PARAMETERS:

* **app\_name** – The app name.  
* **user\_id** – The user ID.  
* **session\_id** – The session ID.  
* **filename** – The filename of the artifact.  
* **version** – The version of the artifact. If None, the latest version will be returned.

RETURNS:  
The artifact or None if not found.

**abstractmethod async save\_artifact(\*, app\_name, user\_id, session\_id, filename, artifact)**  
Saves an artifact to the artifact service storage.

The artifact is a file identified by the app name, user ID, session ID, and filename. After saving the artifact, a revision ID is returned to identify the artifact version.

RETURN TYPE:  
int

PARAMETERS:

* **app\_name** – The app name.  
* **user\_id** – The user ID.  
* **session\_id** – The session ID.  
* **filename** – The filename of the artifact.  
* **artifact** – The artifact to save.

RETURNS:  
The revision ID. The first version of the artifact has a revision ID of 0\. This is incremented by 1 after each successful save.

**class** google.adk.artifacts.**GcsArtifactService(bucket\_name, \*\*kwargs)**  
Bases: [BaseArtifactService](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.artifacts.BaseArtifactService)

An artifact service implementation using Google Cloud Storage (GCS).

Initializes the GcsArtifactService.

PARAMETERS:

* **bucket\_name** – The name of the bucket to use.  
* **\*\*kwargs** – Keyword arguments to pass to the Google Cloud Storage client.

**async delete\_artifact(\*, app\_name, user\_id, session\_id, filename)**  
Deletes an artifact.

RETURN TYPE:  
None

PARAMETERS:

* **app\_name** – The name of the application.  
* **user\_id** – The ID of the user.  
* **session\_id** – The ID of the session.  
* **filename** – The name of the artifact file.

**async list\_artifact\_keys(\*, app\_name, user\_id, session\_id)**  
Lists all the artifact filenames within a session.

RETURN TYPE:  
list\[str\]

PARAMETERS:

* **app\_name** – The name of the application.  
* **user\_id** – The ID of the user.  
* **session\_id** – The ID of the session.

RETURNS:  
A list of all artifact filenames within a session.

**async list\_versions(\*, app\_name, user\_id, session\_id, filename)**  
Lists all versions of an artifact.

RETURN TYPE:  
list\[int\]

PARAMETERS:

* **app\_name** – The name of the application.  
* **user\_id** – The ID of the user.  
* **session\_id** – The ID of the session.  
* **filename** – The name of the artifact file.

RETURNS:  
A list of all available versions of the artifact.

**async load\_artifact(\*, app\_name, user\_id, session\_id, filename, version=None)**  
Gets an artifact from the artifact service storage.

The artifact is a file identified by the app name, user ID, session ID, and filename.

RETURN TYPE:  
Optional\[Part\]

PARAMETERS:

* **app\_name** – The app name.  
* **user\_id** – The user ID.  
* **session\_id** – The session ID.  
* **filename** – The filename of the artifact.  
* **version** – The version of the artifact. If None, the latest version will be returned.

RETURNS:  
The artifact or None if not found.

**async save\_artifact(\*, app\_name, user\_id, session\_id, filename, artifact)**  
Saves an artifact to the artifact service storage.

The artifact is a file identified by the app name, user ID, session ID, and filename. After saving the artifact, a revision ID is returned to identify the artifact version.

RETURN TYPE:  
int

PARAMETERS:

* **app\_name** – The app name.  
* **user\_id** – The user ID.  
* **session\_id** – The session ID.  
* **filename** – The filename of the artifact.  
* **artifact** – The artifact to save.

RETURNS:  
The revision ID. The first version of the artifact has a revision ID of 0\. This is incremented by 1 after each successful save.

**pydantic model** google.adk.artifacts.**InMemoryArtifactService**  
Bases: [BaseArtifactService](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.artifacts.BaseArtifactService), BaseModel

An in-memory implementation of the artifact service.

  
FIELDS:

* artifacts (dict\[str, list\[google.genai.types.Part\]\])

**field artifacts: dict\[str, list\[Part\]\] \[Optional\]**  
**async delete\_artifact(\*, app\_name, user\_id, session\_id, filename)**  
Deletes an artifact.

RETURN TYPE:  
None

PARAMETERS:

* **app\_name** – The name of the application.  
* **user\_id** – The ID of the user.  
* **session\_id** – The ID of the session.  
* **filename** – The name of the artifact file.

**async list\_artifact\_keys(\*, app\_name, user\_id, session\_id)**  
Lists all the artifact filenames within a session.

RETURN TYPE:  
list\[str\]

PARAMETERS:

* **app\_name** – The name of the application.  
* **user\_id** – The ID of the user.  
* **session\_id** – The ID of the session.

RETURNS:  
A list of all artifact filenames within a session.

**async list\_versions(\*, app\_name, user\_id, session\_id, filename)**  
Lists all versions of an artifact.

RETURN TYPE:  
list\[int\]

PARAMETERS:

* **app\_name** – The name of the application.  
* **user\_id** – The ID of the user.  
* **session\_id** – The ID of the session.  
* **filename** – The name of the artifact file.

RETURNS:  
A list of all available versions of the artifact.

**async load\_artifact(\*, app\_name, user\_id, session\_id, filename, version=None)**  
Gets an artifact from the artifact service storage.

The artifact is a file identified by the app name, user ID, session ID, and filename.

RETURN TYPE:  
Optional\[Part\]

PARAMETERS:

* **app\_name** – The app name.  
* **user\_id** – The user ID.  
* **session\_id** – The session ID.  
* **filename** – The filename of the artifact.  
* **version** – The version of the artifact. If None, the latest version will be returned.

RETURNS:  
The artifact or None if not found.

**async save\_artifact(\*, app\_name, user\_id, session\_id, filename, artifact)**  
Saves an artifact to the artifact service storage.

The artifact is a file identified by the app name, user ID, session ID, and filename. After saving the artifact, a revision ID is returned to identify the artifact version.

RETURN TYPE:  
int

PARAMETERS:

* **app\_name** – The app name.  
* **user\_id** – The user ID.  
* **session\_id** – The session ID.  
* **filename** – The filename of the artifact.  
* **artifact** – The artifact to save.

RETURNS:  
The revision ID. The first version of the artifact has a revision ID of 0\. This is incremented by 1 after each successful save.

