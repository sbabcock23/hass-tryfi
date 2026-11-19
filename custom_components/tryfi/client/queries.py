"""TryFi's GraphQL, exactly as pytryfi sends it.

Copied from pytryfi's const.py (Apache 2.0, Steve Babcock) without changing a
character, and composed the way its common/query.py composed them. These are
the queries that work against TryFi today: a changed one cannot be tested
without an account, and a broken one breaks every install at once.
tests/test_queries.py pins a hash of every composed query for that reason.
"""

API_HOST_URL_BASE = "https://api.tryfi.com"
API_GRAPHQL = "/graphql"
API_LOGIN = "/auth/login"
PET_MODE_NORMAL = "NORMAL"
PET_MODE_LOST = "LOST_DOG"
VAR_PET_ID = "__PET_ID__"
QUERY_CURRENT_USER = "query {  currentUser {    ...UserDetails  }}"
QUERY_CURRENT_USER_FULL_DETAIL = "query {  currentUser {    ...UserFullDetails  }}"
QUERY_PET_CURRENT_LOCATION = (
    'query {  pet (id: "'
    + VAR_PET_ID
    + '") {    ongoingActivity {      __typename      ...OngoingActivityDetails    }  }}'
)
QUERY_PET_ACTIVITY = (
    'query {  pet (id: "'
    + VAR_PET_ID
    + '") {       dailyStat: currentActivitySummary (period: DAILY) {      ...ActivitySummaryDetails    }    weeklyStat: currentActivitySummary (period: WEEKLY) {      ...ActivitySummaryDetails    }    monthlyStat: currentActivitySummary (period: MONTHLY) {      ...ActivitySummaryDetails    }  }}'
)
QUERY_PET_REST = (
    'query {  pet (id: "'
    + VAR_PET_ID
    + '") {	dailyStat: restSummaryFeed(cursor: null, period: DAILY, limit: 1) {      __typename      restSummaries {        __typename        ...RestSummaryDetails      }    }	weeklyStat: restSummaryFeed(cursor: null, period: WEEKLY, limit: 1) {      __typename      restSummaries {        __typename        ...RestSummaryDetails      }    }	monthlyStat: restSummaryFeed(cursor: null, period: MONTHLY, limit: 1) {      __typename      restSummaries {        __typename        ...RestSummaryDetails      }    }  }}'
)
QUERY_PET_DEVICE_DETAILS = (
    'query {  pet (id: "' + VAR_PET_ID + '") {    __typename    ...PetProfile  }}'
)
FRAGMENT_USER_DETAILS = "fragment UserDetails on User {  __typename   id  email  firstName  lastName  phoneNumber  fiNewsNotificationsEnabled  chipReseller {    __typename    id  }}"
FRAGMENT_USER_FULL_DETAILS = "fragment UserFullDetails on User {  __typename  ...UserDetails  userHouseholds {    __typename    household {      __typename      pets {        __typename        ...PetProfile      }      bases {        __typename        ...BaseDetails      }    }  }}"
FRAGEMENT_BASE_PET_PROFILE = "fragment BasePetProfile on BasePet {  __typename  id  name  homeCityState  yearOfBirth  monthOfBirth  dayOfBirth  gender  weight  isPurebred  breed {    __typename    ...BreedDetails  }  photos {    __typename    first {      __typename      ...PhotoDetails    }    items {      __typename      ...PhotoDetails    }  }  instagramHandle  }"
FRAGMENT_BREED_DETAILS = (
    "fragment BreedDetails on Breed {  __typename  id  name  popularityScore}"
)
FRAGMENT_PHOTO_DETAILS = "fragment PhotoDetails on Photo {  __typename  id  caption  date  likeCount  liked  image {    __typename    fullSize  }}"
FRAGMENT_PET_PROFILE = "fragment PetProfile on Pet {  __typename  ...BasePetProfile  chip {    __typename    shortId  }  device {    __typename    ...DeviceDetails  }}"
FRAGMENT_DEVICE_DETAILS = "fragment DeviceDetails on Device {  __typename  id  moduleId  info  subscriptionId  hasActiveSubscription  hasSubscriptionOverride  nextLocationUpdateExpectedBy  operationParams {    __typename    ...OperationParamsDetails  }  lastConnectionState {    __typename    ...ConnectionStateDetails  }  ledColor {    __typename    ...LedColorDetails  }  availableLedColors {    __typename    ...LedColorDetails  }}"
FRAGMENT_LED_DETAILS = (
    "fragment LedColorDetails on LedColor {  __typename  ledColorCode  hexCode  name}"
)
FRAGMENT_CONNECTION_STATE_DETAILS = "fragment ConnectionStateDetails on ConnectionState {  __typename  date  ... on ConnectedToUser {    user {      __typename      ...UserDetails    }  }  ... on ConnectedToBase {    chargingBase {      __typename      id    }  }  ... on ConnectedToCellular {    signalStrengthPercent  }  ... on UnknownConnectivity {    unknownConnectivity  }}"
FRAGMENT_OPERATIONAL_DETAILS = "fragment OperationParamsDetails on OperationParams {  __typename  mode  ledEnabled  ledOffAt}"
FRAGMENT_BASE_DETAILS = "fragment BaseDetails on ChargingBase {  __typename  baseId  name  position {    __typename    ...PositionCoordinates  }  infoLastUpdated  networkName  online  onlineQuality}"
FRAGMENT_POSITION_COORDINATES = (
    "fragment PositionCoordinates on Position {  __typename  latitude  longitude}"
)
FRAGMENT_ONGOING_ACTIVITY_DETAILS = "fragment OngoingActivityDetails on OngoingActivity {  __typename  start  presentUser {    __typename    ...UserDetails  }  areaName  lastReportTimestamp  obfuscatedReason  totalSteps  uncertaintyInfo {    __typename    ...UncertaintyInfoDetails  }  ... on OngoingWalk {    distance    positions {      __typename      ...LocationPoint    }    path {      __typename      ...PositionCoordinates    }  }  ... on OngoingRest {    position {      __typename      ...PositionCoordinates    }    place {      __typename      ...PlaceDetails    }  }}"
FRAGMENT_UNCERTAINTY_DETAILS = "fragment UncertaintyInfoDetails on UncertaintyInfo {  __typename  areaName  updatedAt  circle {    __typename    ...CircleDetails  }}"
FRAGMENT_CIRCLE_DETAILS = (
    "fragment CircleDetails on Circle {  __typename  radius  latitude  longitude}"
)
FRAGMENT_LOCATION_POINT = "fragment LocationPoint on Location {  __typename  date  errorRadius  position {    __typename    ...PositionCoordinates  }}"
FRAGMENT_PLACE_DETAILS = "fragment PlaceDetails on Place {  __typename  id  name  address  position {    __typename    ...PositionCoordinates  }  radius}"
FRAGMENT_ACTIVITY_SUMMARY_DETAILS = "fragment ActivitySummaryDetails on ActivitySummary {  __typename  start  end  totalSteps  stepGoal  dailySteps {    __typename    date    totalSteps    stepGoal  }  totalDistance}"
FRAGMENT_REST_SUMMARY_DETAILS = "fragment RestSummaryDetails on RestSummary {  __typename  start  end  data {    __typename    ... on ConcreteRestSummaryData {      sleepAmounts {        __typename        type        duration      }    }  }}"
MUTATION_DEVICE_OPS = "mutation UpdateDeviceOperationParams($input: UpdateDeviceOperationParamsInput!) {  updateDeviceOperationParams(input: $input) {    __typename    ...DeviceDetails  }}"
MUTATION_SET_LED_COLOR = "mutation SetDeviceLed($moduleId: String!, $ledColorCode: Int!) {  setDeviceLed(moduleId: $moduleId, ledColorCode: $ledColorCode) {    __typename    ...DeviceDetails  }}"


def households() -> str:
    """Every pet and base on the account (pytryfi's getPetList)."""
    return (
        QUERY_CURRENT_USER_FULL_DETAIL
        + FRAGMENT_USER_DETAILS
        + FRAGMENT_USER_FULL_DETAILS
        + FRAGMENT_PET_PROFILE
        + FRAGEMENT_BASE_PET_PROFILE
        + FRAGMENT_BASE_DETAILS
        + FRAGMENT_POSITION_COORDINATES
        + FRAGMENT_BREED_DETAILS
        + FRAGMENT_PHOTO_DETAILS
        + FRAGMENT_DEVICE_DETAILS
        + FRAGMENT_LED_DETAILS
        + FRAGMENT_OPERATIONAL_DETAILS
        + FRAGMENT_CONNECTION_STATE_DETAILS
    )


def location(pet_id: str) -> str:
    return (
        QUERY_PET_CURRENT_LOCATION.replace(VAR_PET_ID, pet_id)
        + FRAGMENT_ONGOING_ACTIVITY_DETAILS
        + FRAGMENT_UNCERTAINTY_DETAILS
        + FRAGMENT_CIRCLE_DETAILS
        + FRAGMENT_LOCATION_POINT
        + FRAGMENT_PLACE_DETAILS
        + FRAGMENT_USER_DETAILS
        + FRAGMENT_POSITION_COORDINATES
    )


def activity(pet_id: str) -> str:
    return (
        QUERY_PET_ACTIVITY.replace(VAR_PET_ID, pet_id)
        + FRAGMENT_ACTIVITY_SUMMARY_DETAILS
    )


def rest(pet_id: str) -> str:
    return QUERY_PET_REST.replace(VAR_PET_ID, pet_id) + FRAGMENT_REST_SUMMARY_DETAILS


def set_led_color() -> str:
    return (
        MUTATION_SET_LED_COLOR
        + FRAGMENT_DEVICE_DETAILS
        + FRAGMENT_OPERATIONAL_DETAILS
        + FRAGMENT_CONNECTION_STATE_DETAILS
        + FRAGMENT_USER_DETAILS
        + FRAGMENT_LED_DETAILS
    )


def device_operation() -> str:
    """Turning the LED on or off, and Lost Mode: one mutation, two inputs."""
    return (
        MUTATION_DEVICE_OPS
        + FRAGMENT_DEVICE_DETAILS
        + FRAGMENT_OPERATIONAL_DETAILS
        + FRAGMENT_CONNECTION_STATE_DETAILS
        + FRAGMENT_USER_DETAILS
        + FRAGMENT_LED_DETAILS
    )
