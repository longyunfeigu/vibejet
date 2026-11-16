# language: en
Feature: Diet — Weight trend

  # Source: docs/product/requirements.md (食衡 PRD) — not implemented yet.
  # Activation gate: grep -rn "weight" backend/api/routes frontend/src/features

  @DIET-WGT-001 @smoke
  Scenario: The weight page is ready for input and shows the trend area
    Given a diet user with the standard profile
    When I open the weight page
    Then the weight input should be ready
    And the weight trend area should be visible

  @DIET-WGT-002 @regression
  Scenario: The last weight of the day wins
    Given a diet user with the standard profile
    When I record a weight of "60.4" kg today
    And I record a weight of "60.1" kg today
    Then today should have one weight point of "60.1" kg
    And after reloading the page today's weight should still be "60.1" kg

  @DIET-WGT-003 @regression
  Scenario: Saying a weight in chat records today's weight, not a meal
    Given a diet user with the standard profile
    When I send "今天 65.2"
    Then today's weight should be "65.2" kg
    And no new meal should be recorded

  @DIET-WGT-004 @regression
  Scenario Outline: Weights on the edge of the allowed range are accepted
    Given a diet user with the standard profile
    When I record a weight of "<kg>" kg today
    Then today should have one weight point of "<kg>" kg

    Examples:
      | kg |
      | 30 |
      | 300 |

  @DIET-WGT-005 @negative
  Scenario Outline: Out-of-range or malformed weights are rejected
    Given a diet user with the standard profile
    When I record a weight of "<kg>" kg today
    Then the weight field should show an error
    And today should have no weight point

    Examples:
      | kg |
      | 29.9 |
      | 300.1 |
      |  |
      | 六十 |

  @DIET-WGT-006 @regression
  Scenario Outline: A jump of more than 3 kg asks the user to double-check
    Given a diet user with the standard profile and a weight of "60.0" kg yesterday
    When I record a weight of "<kg>" kg today
    Then the double-check prompt should be "<shown>"

    Examples:
      | kg | shown |
      | 63.0 | not shown |
      | 63.1 | shown |

  @DIET-WGT-007 @regression
  Scenario Outline: With fewer than 7 recorded days only daily points are shown
    Given a diet user with weights on "<days>" days
    When I open the weight page
    Then only daily weight points should be shown
    And the page should say "<left>" more days are needed
    And there should be no 7-day average line and no expected date

    Examples:
      | days | left |
      | 1 | 6 |
      | 6 | 1 |

  @DIET-WGT-008 @regression
  Scenario: The 7-day average uses only recorded days, with a goal line and range switch
    Given a diet user with weights over the last "10" days except "3" days ago
    When I open the weight page
    Then the latest 7-day average should be the mean of the recorded days in the last 7 days
    And the goal line should be at "55" kg
    When I switch the range to "3 个月" and back to "4 周"
    Then each range should show the recorded points inside it

  @DIET-WGT-009 @regression
  Scenario: Enough downward data shows the distance to goal and an expected date
    Given a diet user with "10" weights over the last "28" days trending down
    When I open the weight page
    Then the page should show how many kg are left to the goal
    And the expected date should equal the precomputed date

  @DIET-WGT-010 @negative
  Scenario Outline: No expected date before 28 days or 7 recorded days
    Given a diet user whose first weight was "<span>" days ago with "<days>" recorded days
    When I open the weight page
    Then no expected date should be shown

    Examples:
      | span | days |
      | 27 | 10 |
      | 28 | 6 |

  @DIET-WGT-011 @negative
  Scenario: No expected date when the trend moves away from the goal
    Given a diet user with "10" weights over the last "28" days trending up recently
    When I open the weight page
    Then no expected date should be shown
    And the page should describe the recent change

  @DIET-WGT-012 @negative
  Scenario: A user cannot reach another user's weights
    Given two diet users "A" and "B"
    And user "A" has weight records
    When user "B" reads, edits and deletes user "A"'s weights
    Then every request should be answered as not found
    And user "A"'s weights should be unchanged
