# language: en
Feature: Auth — Login

  # Every project starts signed in as the test account (config/global-setup.ts);
  # signed-out scenarios drop that session first.

  @AUTH-LGN-001 @smoke
  Scenario: A signed-out visitor who opens the home page is sent to the login page
    Given I am signed out
    When I open the home page
    Then I should be on the login page
    And the login form should show the "用户名或邮箱" and "密码" fields

  @AUTH-LGN-002 @regression
  Scenario: The test account signs in and lands on the home page greeting
    Given I am signed out
    When I sign in as the test account
    Then the home page should greet the test account
    And the account API should report the test account as signed in

  @AUTH-LGN-003 @negative
  Scenario: A wrong password keeps the visitor on the login page with an error
    Given I am signed out
    When I sign in as the test account with the password "wrong-password-e2e"
    Then I should be on the login page
    And the login error "Invalid username or password" should be shown
    And no session should be stored

  @AUTH-LGN-004 @negative
  Scenario: Submitting an empty login form shows both required-field messages
    Given I am signed out
    When I submit the empty login form
    Then the field message "请输入用户名或邮箱" should be shown
    And the field message "请输入密码" should be shown
    And I should be on the login page

  @AUTH-LGN-005 @regression
  Scenario: Signing out returns to the login page and protects the home page
    When I open the home page
    And I sign out from the top bar
    Then I should be on the login page
    When I open the home page
    Then I should be on the login page
