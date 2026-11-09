# language: en
Feature: Home — Dashboard

  @HOME-DSH-001 @smoke
  Scenario: A signed-in user sees the greeting and the dashboard sections
    When I open the home page
    Then the home page should greet the test account
    And the dashboard sections "最近动态" and "质量门禁" should be visible
    And the top bar should offer "退出"

  @HOME-DSH-002 @negative
  Scenario: A session the backend rejects shows the session-expired page and leads back to login
    Given my stored session holds tokens the backend rejects
    When I open the home page
    Then I should see the session-expired page
    And no session should be stored
    When I choose to sign in again
    Then I should be on the login page
