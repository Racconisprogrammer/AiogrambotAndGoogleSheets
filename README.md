# Obtaining Google API Credentials

To use Google APIs and access Google services programmatically, you need to obtain credentials. Follow the steps below to set up credentials for your project:

1. **Go to Google Cloud Console:**

   - Open [Google Cloud Console](https://console.cloud.google.com/).
   - In the upper right corner, select or create a project.

2. **Enable the required APIs:**

   - In the left-hand menu, select "APIs & Services" > "Library".
   - Find and enable the necessary APIs for your project, such as Google Drive API, Google Sheets API, and others.

3. **Set up credentials:**

   - Navigate to "APIs & Services" > "Credentials".
   - Click on "Create Credentials" and choose the appropriate credential type:
     - For web applications, choose "OAuth client ID".
     - For server-to-server interactions, choose "Service account key".
   - Follow the prompts to complete the setup, specifying API permissions and downloading the credentials file.

4. **Use the credentials in your code:**
   - Once you have the credentials file, integrate it into your code to authenticate requests to the Google APIs.

Note: The exact steps and options may vary depending on the specific Google API you are working with. Always refer to the documentation of the particular API for detailed and accurate instructions.

# Getting Started

To run this project, follow the steps below:

1. **Obtain BotFather Token:**

   - Obtain a BotFather token for your Telegram bot. If you don't have one, create a new bot on Telegram and get the token from BotFather.

2. **Replace Configuration Files:**
   - Replace the following files using the instructions provided above:
     - `client_secrets.json.public` with `client_secrets.json`
     - `credentials.json.public` with `credentials.json`

This ensures that your project is configured with the necessary credentials and settings. The `client_secrets.json` file typically contains information related to the OAuth client ID, and `credentials.json` is used for authentication.

Make sure to keep these files secure and do not expose them publicly, as they contain sensitive information.

Feel free to reach out if you have any questions or need further assistance.
