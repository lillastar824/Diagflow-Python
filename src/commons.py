AUTHENTICATION_NO_INPUT_1 = [
    "Sorry, I didn't get that. Could you repeat that?"
]
AUTHENTICATION_NO_INPUT_2 = [
    "Sorry, I didn't get that. Could you repeat that?"
]
AUTHENTICATION_NO_MATCH_1 = [
    "Sorry, I didn't get that. Could you repeat that?"
]
AUTHENTICATION_NO_MATCH_2 = ["Sorry, What is your first and last name?"]
COLLECT_NAME_PROMPT = "What’s your first and last name?"
COLLECT_NAME_OK = "Ok!"
NAME_NO_INPUT_1 = ["Sorry, What is your first and last name?"]
NAME_NO_INPUT_2 = ["Sorry, What is your first and last name?"]
NAME_NO_MATCH_1 = ["Sorry, What is your first and last name?"]
NAME_NO_MATCH_2 = ["Sorry, What is your first and last name?"]

SCHEDULING_DESIRED_ACTION_NO_INPUT_1 = (
    "<speak>"
    '<emphasis level="strong">Would you like to verify, cancel, reschedule,'
    'or <phoneme alphabet="ipa" ph="meɪk">make</phoneme> an appointment?'
    "</emphasis></speak>"
)
SCHEDULING_DESIRED_ACTION_NO_INPUT_2 = (
    "<speak>I’m sorry, I couldn’t hear you. Would you like to "
    '<emphasis level="strong">verify</emphasis><break time="200ms"/>, '
    '<emphasis level="strong">cancel</emphasis><break time="200ms"/>, '
    '<emphasis level="strong">reschedule</emphasis><break time="200ms"/>, '
    'or <emphasis level="strong">'
    '<phoneme alphabet="ipa" ph="meɪk">make</phoneme></emphasis>'
    '<break time="100ms"/> an appointment?</speak>'
)
SCHEDULING_DESIRED_ACTION_NO_MATCH_1 = (
    "<speak>I’m sorry. "
    '<emphasis level="strong">Would you like to verify, cancel, reschedule, '
    'or <phoneme alphabet="ipa" ph="meɪk">make</phoneme> an appointment?'
    "</emphasis></speak>"
)
SCHEDULING_DESIRED_ACTION_NO_MATCH_2 = (
    "<speak>I’m not sure I can do that. "
    '<emphasis level="strong">Would you like to verify, cancel, reschedule, '
    'or <phoneme alphabet="ipa" ph="meɪk">make</phoneme> an appointment?'
    "</emphasis></speak>"
)

TRANSFERRING_TO_AGENT_FAILED = (
    '<speak><prosody pitch="-3st">I’m going to transfer you '
    "to the next available scheduler who can help you!</prosody></speak>"
)
TRANSFERRING_TO_AGENT_SUCCESS = (
    '<speak><prosody pitch="+2st" rate="medium">'
    '<emphasis level="strong">I’m going to transfer you</emphasis> '
    "to the next available scheduler "
    '<emphasis level="strong">who can help you</emphasis>!</prosody></speak>'
)

DEFAULT_WELCOME_INTENT_HELLO = "Hello."
PROMPT_FOR_SCHEDULING = (
    '<speak>Would you like to <emphasis level="strong">verify</emphasis>'
    '<break time="200ms"/>, '
    '<emphasis level="strong">cancel</emphasis><break time="200ms"/>, '
    '<emphasis level="strong">reschedule</emphasis>'
    '<break time="200ms"/>, '
    'or <emphasis level="strong">'
    '<phoneme alphabet="ipa" ph="meɪk">make</phoneme></emphasis>'
    '<break time="100ms"/> an appointment?</speak>'
)

CREATE_APPOINTMENT_PROMPT = (
    '<speak>And, are you a <emphasis level="moderate">new</emphasis>'
    '<break time="200ms"/> '
    'or <emphasis level="strong">established</emphasis>'
    '<break time="100ms"/> patient?</speak>'
)
CREATE_APPOINTMENT_I_DONT_KNOW = (
    "Ok, I can authenticate you and search for your chart."
)
CREATE_APPOINTMENT_NO_INPUT_1 = (
    '<speak>Are you a <emphasis level="moderate">new</emphasis>'
    '<break time="200ms"/> '
    'or <emphasis level="strong">established</emphasis>'
    '<break time="100ms"/> patient?</speak>'
)
CREATE_APPOINTMENT_NO_INPUT_2 = (
    "I’m sorry, I can’t hear you. Have you made an appointment at "
    "$session.params.friendly_practice_name before?"
)
CREATE_APPOINTMENT_NO_MATCH_1 = (
    "I need to verify if you are a new or established patient. Have you "
    "been to $session.params.friendly_practice_name before?"
)
CREATE_APPOINTMENT_NO_MATCH_2 = (
    "<speak>Before we do anything else, I need to confirm: are you a "
    '<emphasis level="strong">new</emphasis><break time="100ms"/> or '
    '<emphasis level="strong">established</emphasis> patient?</speak>'
)

DESIRED_ACTION_PROMPT = {
    "appointment.routing.existing": (
        "Great, I can help you verify your appointment. "
        "First, let me look up your chart."
    ),
    "appointment.routing.cancel": (
        "Ok. to cancel your appointment, we'll need to pull up your chart."
    ),
    "appointment.routing.reschedule": (
        "Ok. to reschedule your appointment, "
        "we'll need to pull up your chart."
    ),
    "appointment.routing.new_app": (
        "Ok. to make an appointment, we'll need to pull up your chart."
    ),
}

ANYTHING_ELSE_PROMPT = "Is there anything else I can help you with?"
ASK_ANYTHING_ELSE_NO_INPUT_1 = "Is there anything else I can help you with?"
ASK_ANYTHING_ELSE_NO_INPUT_2 = (
    "I’m sorry, I couldn’t hear you. "
    "Is there anything else I can help you with today?"
)
ASK_ANYTHING_ELSE_NO_MATCH_1 = (
    '<speak>I’m sorry. I can only <emphasis level="strong">verify</emphasis>'
    '<break time="200ms"/>, '
    '<emphasis level="strong">cancel</emphasis><break time="200ms"/>, '
    '<emphasis level="strong">reschedule</emphasis>'
    '<break time="200ms"/>, or '
    '<emphasis level="strong">'
    '<phoneme alphabet="ipa" ph="meɪk">make</phoneme></emphasis>'
    '<break time="100ms"/> '
    "appointments. What else would you like to do?</speak>"
)

ASK_ANYTHING_ELSE_NO_MATCH_2 = (
    "<speak>I’m not sure I can do that. I'm able to "
    '<emphasis level="strong">verify</emphasis><break time="200ms"/>, '
    '<emphasis level="strong">cancel</emphasis><break time="200ms"/>, '
    '<emphasis level="strong">reschedule</emphasis>'
    '<break time="200ms"/>, or '
    '<emphasis level="strong">'
    '<phoneme alphabet="ipa" ph="meɪk">make</phoneme></emphasis>'
    '<break time="100ms"/> '
    "appointments. What would you like to do today?</speak>"
)

CONFIRM_BLOCK_PROMPT = "I heard XYZ. Is that right?"
CONFIRM_PATTERN_CONFIRM_PAGE_NO_INPUT_1 = (
    "Sorry I didn't get that! $session.params.confirm_text"
)
CONFIRM_PATTERN_CONFIRM_PAGE_NO_INPUT_2 = (
    "Sorry I didn't get that! $session.params.confirm_text"
)
CONFIRM_PATTERN_CONFIRM_PAGE_NO_MATCH_1 = (
    "Sorry I didn't get that! $session.params.confirm_text"
)
CONFIRM_PATTERN_CONFIRM_PAGE_NO_MATCH_2 = (
    "Sorry I didn't get that! $session.params.confirm_text"
)
SPEAK_PROVIDER_NAME = (
    "Thank you for choosing $session.params.friendly_practice_name."
    " Have a great day and goodbye."
)

OFFICE_HOURS_CLOSED = "Office is closed"
