import pytest
from sqlalchemy.orm import Session
from backend.models.ni_document import NIDocumentCreate
from backend.services.ni import NIService
from backend.test.services.fixtures import compile_all_tokens_for_doc, mock_llm_side_effect
from backend.services.llm.openai_llm_client import OpenAILLMClient
from typing import Callable, Any
from backend.services.llm.base_llm_client import BaseLLMClient
from backend.test.services.fixtures import llm_client
import logging

logging.basicConfig(level=logging.INFO)
"""This test should not be run with less than 10 inputs."""
# Define realistic NI document test inputs
TEST_INPUTS = [
    # Test Input 1: Simple Introduction Scene
    """[Scene:Intro]
The user enters the application and should receive a friendly greeting.
[Component:Greeting]
Display a personalized greeting message to the user.
[Function:displayGreeting]
Show "Welcome back, John! How can we assist you today?" in the greeting area.
[Function:logEntry]
Log the user's entry time and IP address for security auditing.""",

    # Test Input 2: Login Process with Error Handling
    """[Scene:Login]
The user needs to authenticate to access their account.
[Component:LoginForm]
Provide fields for username and password entry.
[Function:validateCredentials]
Verify the entered username and password against the database.
If credentials are invalid, increment failed login attempts.
[Function:displayError]
Show an error message if the credentials are incorrect.
If failed attempts exceed 5, lock the account and notify the user via email.""",

    # Test Input 3: User Dashboard with Conditional Components
    """[Scene:Dashboard]
After logging in, the user should see an overview of their account.
[Component:StatisticsPanel]
Display key user statistics such as active projects and recent activity.
[Function:fetchStatistics]
Retrieve user statistics from the server and display them in charts.
If the user has no active projects, show a prompt to create one.
[Component:QuickActions]
Provide shortcuts to frequently used features like "Create New Project" and "View Reports."
[Function:navigateToFeature]
Redirect the user to the selected feature when a quick action is clicked.
If navigating to "View Reports," ensure the user has the necessary permissions.""",

    # Test Input 4: Profile Management with Validation
    """[Scene:UserProfile]
The user wants to view and edit their personal information.
[Component:ProfileDetails]
Show the user's name, email, and contact information.
[Function:editProfile]
Allow the user to update their personal details and save changes.
Ensure all mandatory fields are filled and email format is correct.
[Component:Preferences]
Enable the user to set their preferences, such as notification settings and display options.
[Function:savePreferences]
Store the user's preference settings in the database.
[Function:validatePreferences]
Ensure that preferences meet system constraints, such as notification frequency limits.""",

    # Test Input 5: Notification Center with Real-time Updates
    """[Scene:Notifications]
The user should be informed about recent updates and messages.
[Component:NotificationList]
Display a list of unread and recent notifications.
[Function:markAsRead]
Allow the user to mark notifications as read.
[Function:fetchNotifications]
Retrieve the latest notifications from the server and update the list.
If the server is unreachable, show a retry option.
[Component:NotificationSettings]
Provide options for the user to customize their notification preferences.
[Function:updateSettings]
Save the user's notification preferences based on their selections.
[Function:pushNotification]
Send real-time push notifications for critical updates.""",

    # Test Input 6: Multi-Step Wizard with Data Persistence
    """[Scene:WizardStep1]
The user begins the setup process with an introduction.
[Component:Introduction]
Provide an overview of what the setup will entail.
[Function:proceedToStep2]
Move the user to the next step when they click "Next."

[Scene:WizardStep2]
The user inputs their personal information.
[Component:PersonalInfoForm]
Include fields for name, email, and phone number.
[Function:validatePersonalInfo]
Ensure all required fields are filled out correctly.
[Function:savePersonalInfo]
Store the entered personal information in the user's profile.
If the email already exists, prompt the user to log in instead.

[Scene:WizardStep3]
The user configures their preferences.
[Component:PreferencesForm]
Allow the user to select their preferred settings.
[Function:applyPreferences]
Apply the selected preferences to the user's account.
[Function:completeSetup]
Finalize the setup process and redirect the user to the dashboard.
Send a confirmation email upon successful setup.""",

    # Test Input 7: E-commerce Checkout Process with Inventory Check
    """[Scene:CartReview]
The user reviews items in their shopping cart.
[Component:CartItems]
List all items with quantities and prices.
[Function:updateQuantity]
Allow the user to change the quantity of each item.
Ensure that the requested quantity is available in inventory.
[Function:removeItem]
Enable the user to remove items from the cart.

[Scene:ShippingDetails]
The user enters their shipping information.
[Component:ShippingForm]
Provide fields for address, city, state, and zip code.
[Function:validateAddress]
Ensure the shipping address is complete and valid.
[Function:saveShippingInfo]
Store the shipping details for order processing.
If the address is invalid, prompt the user to correct it.

[Scene:Payment]
The user selects a payment method and enters payment details.
[Component:PaymentOptions]
Offer various payment methods such as credit card, PayPal, and gift card.
[Function:processPayment]
Handle the payment transaction securely.
If the payment fails, notify the user and allow retry.
[Function:displayReceipt]
Show an order receipt upon successful payment.
Include order summary and estimated delivery date.""",

    # Test Input 8: Account Settings with Security Features
    """[Scene:AccountSettings]
The user wants to manage their account preferences and security.
[Component:ChangePassword]
Provide fields to enter the current password and the new password.
[Function:validatePassword]
Ensure the new password meets security requirements (e.g., length, complexity).
[Function:updatePassword]
Update the user's password in the system.
If the current password is incorrect, notify the user.

[Component:TwoFactorAuth]
Enable the user to set up two-factor authentication for added security.
[Function:enable2FA]
Activate two-factor authentication and send a verification code.
[Function:verify2FA]
Confirm the entered verification code to complete the setup.
[Function:disable2FA]
Allow the user to disable two-factor authentication after re-authentication.""",

    # Test Input 9: Help and Support with Search and Feedback
    """[Scene:HelpCenter]
The user seeks assistance with using the application.
[Component:FAQSection]
Display a list of frequently asked questions and answers.
[Function:searchFAQ]
Allow the user to search for specific topics within the FAQs.
[Function:filterFAQ]
Enable filtering FAQs by categories or tags.
[Component:ContactSupport]
Provide options for the user to reach out to customer support.
[Function:submitSupportTicket]
Allow the user to submit a support ticket with their query or issue.
[Function:trackSupportTicket]
Enable users to track the status of their submitted support tickets.
[Function:provideFeedback]
Allow users to rate their support experience and provide feedback.""",

    # Test Input 10: Reporting Module with Data Export and Visualization
    """[Scene:Reports]
The user needs to generate and view various reports.
[Component:ReportFilters]
Offer filters such as date range, report type, and categories.
[Function:applyFilters]
Filter the available reports based on the selected criteria.
[Component:ReportViewer]
Display the generated report in a readable format with charts and tables.
[Function:exportReport]
Allow the user to export the report in formats like PDF or Excel.
[Function:generateChart]
Create visual charts based on the report data.
[Function:saveReportPreferences]
Store the user's preferred report settings for future use.""",

    # Test Input 11: User Registration with Email Verification
    """[Scene:Registration]
A new user wants to create an account.
[Component:RegistrationForm]
Provide fields for username, email, password, and password confirmation.
[Function:validateRegistration]
Ensure all fields are filled out correctly and passwords match.
[Function:createUser]
Create a new user account in the database.
[Function:sendWelcomeEmail]
Send a welcome email to the newly registered user.
[Function:verifyEmail]
Confirm the user's email address through a verification link.
[Function:displaySuccess]
Show a success message upon successful registration and email verification.""",

    # Test Input 12: Password Recovery with Rate Limiting
    """[Scene:PasswordRecovery]
A user has forgotten their password and wants to reset it.
[Component:PasswordRecoveryForm]
Provide a field for the user to enter their registered email address.
[Function:validateEmail]
Check if the entered email exists in the database.
[Function:sendRecoveryLink]
Send a password recovery link to the user's email.
[Function:displayRecoveryMessage]
Show a message indicating that a recovery link has been sent.
[Function:rateLimitRecovery]
Limit the number of recovery requests to prevent abuse.
[Function:handleRecoveryError]
Display appropriate messages if the recovery process fails.""",

    # Test Input 13: User Roles and Permissions with Audit Logs
    """[Scene:RoleManagement]
Administrators manage user roles and permissions.
[Component:RoleAssignment]
Provide options to assign roles (e.g., Admin, Editor, Viewer) to users.
[Function:assignRole]
Assign the selected role to the specified user.
[Function:validateRole]
Ensure that the role being assigned is valid and permitted.
[Component:PermissionSettings]
Allow administrators to customize permissions for each role.
[Function:updatePermissions]
Update the permissions associated with a specific role.
[Function:displayRoleUpdate]
Show a confirmation message after successfully updating roles or permissions.
[Function:logRoleChange]
Log all role and permission changes for auditing purposes.""",

    # Test Input 14: Data Export with Large Data Handling
    """[Scene:DataExport]
The user wants to export their data for offline use.
[Component:ExportOptions]
Provide options for export formats (e.g., CSV, JSON, XML).
[Function:selectExportFormat]
Allow the user to choose their preferred export format.
[Function:generateExport]
Generate the data export in the selected format.
[Function:handleLargeExports]
Manage large data exports by splitting files or using compression.
[Function:downloadExport]
Provide a download link for the exported data.
[Function:notifyExportComplete]
Notify the user when the export is ready for download.
[Function:validateExport]
Ensure the exported data integrity before providing it to the user.""",

    # Test Input 15: Real-time Chat Support with Session Management
    """[Scene:ChatSupport]
The user needs immediate assistance via live chat.
[Component:ChatWindow]
Display a real-time chat interface for user and support agent communication.
[Function:sendMessage]
Send the user's message to the support agent.
[Function:receiveMessage]
Receive and display the support agent's response.
[Function:handleTyping]
Show a typing indicator when the support agent is composing a response.
[Function:endChat]
Allow the user to end the chat session gracefully.
[Function:saveChatHistory]
Save the chat history for future reference.
[Function:validateSession]
Ensure that chat sessions are securely managed and isolated.""",

    # Test Input 16: File Upload and Management with Security Checks
    """[Scene:FileUpload]
The user needs to upload and manage files within the application.
[Component:UploadForm]
Provide fields for selecting and uploading files.
[Function:validateFile]
Ensure the uploaded file meets size and format requirements.
[Function:scanFileForViruses]
Scan uploaded files for malware or viruses before saving.
[Function:uploadFile]
Handle the file upload process to the server.
[Component:FileList]
Display a list of uploaded files with options to view, download, or delete.
[Function:deleteFile]
Allow the user to delete selected files from their account.
[Function:downloadFile]
Enable the user to download their uploaded files.
[Function:displayUploadSuccess]
Show a success message after a file is successfully uploaded.
[Function:handleUploadError]
Display error messages if the upload fails due to security checks or server issues.""",

    # Test Input 17: Multi-language Support with Dynamic Content Translation
    """[Scene:Localization]
The user prefers to use the application in a different language.
[Component:LanguageSelector]
Provide options for selecting the desired language (e.g., English, Spanish, French).
[Function:setLanguage]
Set the application's language based on user selection.
[Function:translateContent]
Translate all user-facing text to the selected language.
[Function:loadLocaleResources]
Load additional resources required for the selected language.
[Function:displayLanguageChange]
Show a confirmation message after successfully changing the language.
[Function:handleTranslationErrors]
Gracefully handle any errors that occur during the translation process.""",

    # Test Input 18: Activity Logs and Auditing with Search and Filter
    """[Scene:ActivityLogs]
Administrators need to review user activity for auditing purposes.
[Component:LogViewer]
Display a list of user activities with filters for date range, user, and activity type.
[Function:fetchLogs]
Retrieve activity logs from the server based on selected filters.
[Function:filterLogs]
Allow administrators to apply additional filters to the displayed logs.
[Function:exportLogs]
Enable the export of activity logs in formats like CSV or PDF.
[Function:displayLogDetails]
Show detailed information about a selected log entry.
[Function:searchLogs]
Provide a search functionality to find specific log entries.
[Function:validateLogAccess]
Ensure that only authorized administrators can access and view activity logs.""",

    # Test Input 19: API Integration with Error Handling and Retries
    """[Scene:APIIntegration]
The application integrates with external third-party APIs.
[Component:APIConnector]
Provide fields to input API credentials and endpoints.
[Function:validateAPIKeys]
Ensure the provided API keys are valid and have necessary permissions.
[Function:connectToAPI]
Establish a connection to the third-party API.
[Function:fetchAPIData]
Retrieve data from the connected API and display it within the application.
[Function:handleAPIError]
Gracefully handle any errors or issues that arise during API communication.
[Function:retryAPIRequest]
Implement retry logic for transient API failures.
[Function:logAPIInteractions]
Log all interactions with the third-party API for monitoring and auditing.""",

    # Test Input 20: Accessibility Features with Compliance Checks
    """[Scene:Accessibility]
Ensure the application is accessible to all users, including those with disabilities.
[Component:AccessibilitySettings]
Provide options to adjust text size, contrast, and enable screen reader support.
[Function:adjustTextSize]
Allow users to increase or decrease the text size for better readability.
[Function:toggleContrast]
Enable high-contrast mode for users with visual impairments.
[Function:enableScreenReader]
Activate screen reader support to assist visually impaired users.
[Function:validateAccessibilitySettings]
Ensure that accessibility settings are applied correctly and persist across sessions.
[Function:displayAccessibilityConfirmation]
Show a confirmation message after successfully applying accessibility settings.
[Function:checkWCAGCompliance]
Validate that the application meets WCAG (Web Content Accessibility Guidelines) standards.
[Function:handleAccessibilityErrors]
Provide feedback if accessibility features fail to apply correctly.""",
]


@pytest.mark.benchmark(group="ni_creation_varied")
@pytest.mark.parametrize("ni_content", TEST_INPUTS)
def test_ni_creation_varied(benchmark: Callable[[Callable[[], Any]], Any], db_session: Session, ni_content: str, llm_client: BaseLLMClient) -> None:
    """
    Benchmark NI creation and compilation with different, realistic narrative instructions.
    Also capture token usage and cost from the LLM after compilation.
    """

    def create_and_compile():
        doc_data = NIDocumentCreate(content=ni_content, version="v1")

        # Instantiate the LLM client
        ni_service = NIService(llm_client)

        # Pass the client into create_ni_document for dependency injection
        ni_doc = ni_service.create_ni_document(doc_data, db_session, llm_client=llm_client)
        compile_all_tokens_for_doc(ni_doc.id, db_session, llm_client)

        # After compilation, retrieve the last used LLM client and gather usage & cost
        used_client = NIService.get_last_llm_client()
        usage_info = {}
        if used_client and used_client.last_usage:
            usage_info = {
                "prompt_tokens": used_client.last_usage.prompt_tokens, # type: ignore
                "completion_tokens": used_client.last_usage.completion_tokens, # type: ignore
                "total_tokens": used_client.last_usage.total_tokens, # type: ignore
                "cost": used_client.last_cost
            }
        benchmark.extra_info = usage_info
        return usage_info

    benchmark(create_and_compile)