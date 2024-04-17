"""
Create the Find Existing Appointment flow

Requirements:
1. patient_id is available in session variables
2. get list of appointments to see if the patient has any
3. provide the list of appointments to the patient
4. ask for date if not correct one
5. ask for provider if doesn't have date
6. once an appointment is successfully found and described,
   set the appointment_id variable. Next step after flow will ask about
   taking the action on the appointment

Naming Conventions:
> Interaction with User
* Webhook Call
- Internal Task eg Set Variables, etc

Flow:
A >> B (C) means A transitions to B when C is true
"""

import time

from google.cloud.dialogflowcx_v3 import Flow

import utils
from library import DialogflowLibrary as dl
from library import StandardPage, SystemEntityType


def create_existing_appointment_flow_pages(config) -> Flow:
    time.sleep(60)

    flow_name = utils.FlowNames.FIND_EXISTING_APPOINTMENT
    utils.delete_flow_with_check(flow_display_name=flow_name, config=config)

    # common elements
    intent_yes = dl.get_intent("prebuilt_components_confirmation_yes")
    intent_no = dl.get_intent("prebuilt_components_confirmation_no")
    intent_agent_transfer = dl.get_intent(
        "prebuilt_components_escalate_human_agent"
    )

    no_match_1_fulfillment = dl.create_fulfillment(
        messages=[
            dl.create_response_message(
                text="Sorry, I didn’t understand you. Could you say it again?"
            ),
        ],
    )
    no_match_2_fulfillment = dl.create_fulfillment(
        messages=[
            dl.create_response_message(
                text="Sorry, I don't understand. Could you say it again?"
            ),
        ],
    )

    no_input_1_fulfillment = dl.create_fulfillment(
        messages=[
            dl.create_response_message(
                text="Sorry, I didn’t get that. Could you say it again?"
            ),
        ],
    )
    no_input_2_fulfillment = dl.create_fulfillment(
        messages=[
            dl.create_response_message(
                text="Sorry, I didn’t catch that. Could you say it again?"
            ),
        ],
    )

    standard_match_event_handlers = [
        dl.create_event_handler(
            # name="no-match-1",
            event="sys.no-match-1",
            trigger_fulfillment=no_match_1_fulfillment,
        ),
        dl.create_event_handler(
            # name="no-match-2",
            event="sys.no-match-2",
            trigger_fulfillment=no_match_2_fulfillment,
        ),
        dl.create_event_handler(
            # name="no-input-1",
            event="sys.no-input-1",
            trigger_fulfillment=no_input_1_fulfillment,
        ),
        dl.create_event_handler(
            # name="no-input-2",
            event="sys.no-input-2",
            trigger_fulfillment=no_input_2_fulfillment,
        ),
    ]

    date_entity_type = dl.get_system_entity_type(SystemEntityType.DATE)
    time_entity_type = dl.get_system_entity_type(SystemEntityType.TIME)
    any_entity_type = dl.get_system_entity_type(SystemEntityType.ANY)

    # create the new flow
    find_existing_appointment_flow = dl.create_flow(
        utils.FlowNames.FIND_EXISTING_APPOINTMENT
    )

    end_flow_page = dl.get_standard_page(
        flow=find_existing_appointment_flow,
        page=StandardPage.END_FLOW,
    )

    end_human_escalation_page = dl.get_standard_page(
        flow=find_existing_appointment_flow,
        page=StandardPage.END_FLOW_WITH_HUMAN_ESCALATION,
    )

    end_failure_page = dl.get_standard_page(
        flow=find_existing_appointment_flow,
        page=StandardPage.END_FLOW_WITH_FAILURE,
    )

    dl.update_flow(
        flow=find_existing_appointment_flow,
        event_handlers=[
            dl.create_event_handler(
                # name="human-escalation-failure",
                event="flow.failed.human-escalation",
                target_page=end_human_escalation_page,
            ),
            dl.create_event_handler(
                # name="failure",
                event="flow.failed",
                target_page=end_failure_page,
            ),
        ],
    )

    # get appointments needs the following session params:
    # - patientId (required)
    # - appointment_date (can be null)
    # - provider_name (can be null)
    # - appointments_limit (can be null)
    get_appointments_webhook = dl.get_webhook(utils.WebHookNames.DIAGFLOW)

    # prepare the required webhook variables with null values
    initialize_webhook_set_vars_task = dl.create_page(
        flow=find_existing_appointment_flow,
        page_name="> Set Webhook Variables",
        entry_fulfillment=dl.create_fulfillment(
            set_parameter_actions=[
                dl.create_set_parameter_action(
                    parameter="appointment_date",
                    value=None,
                ),
                dl.create_set_parameter_action(
                    parameter="provider_name",
                    value=None,
                ),
                dl.create_set_parameter_action(
                    parameter="appointments_limit",
                    value=None,
                ),
            ],
        ),
    )

    # when successfully complete, need to set the appointment variable
    # to the correct appointment
    complete_with_first_appointment_set_var_task = dl.create_page(
        flow=find_existing_appointment_flow,
        page_name="- Set Appointment ID to First Appointment",
        entry_fulfillment=dl.create_fulfillment(
            set_parameter_actions=[
                dl.create_set_parameter_action(
                    parameter="appointment_id",
                    value="$session.params.first_appointment.appointmentId",
                ),
            ],
        ),
    )

    # set_to_first_appointment_var_task >> continue_existing_appointment
    # (always)
    dl.add_transition_route(
        parent=complete_with_first_appointment_set_var_task,
        transition=dl.create_transition_route(
            condition="true",
            target_page=end_flow_page,
        ),
    )

    # find_existing_appointment_flow >> set_webhook_vars_task (always)
    dl.add_transition_route(
        parent=find_existing_appointment_flow,
        transition=dl.create_transition_route(
            condition="true",
            target_page=initialize_webhook_set_vars_task,
        ),
    )

    # fetch all the appointments to start the flow
    get_all_appointments_call_webhook_task = dl.create_page(
        flow=find_existing_appointment_flow,
        page_name="* Get The Next Few Appointments",
        entry_fulfillment=dl.create_fulfillment(
            webhook=get_appointments_webhook,
            tag="find_appointments",
            set_parameter_actions=[
                dl.create_set_parameter_action(
                    parameter="appointments_limit",
                    value=4,
                ),
            ],
        ),
        event_handlers=[
            dl.create_event_handler(
                # name="error",
                event="webhook.error",
                target_page=end_failure_page,
            ),
        ],
    )

    # set_webhook_vars_task >> get_all_appointments_call_webhook_task (always)
    dl.add_transition_route(
        parent=initialize_webhook_set_vars_task,
        transition=dl.create_transition_route(
            condition="true",
            target_page=get_all_appointments_call_webhook_task,
        ),
    )

    # get_all_appointments_call_webhook_task >> end_human_escalation_page
    # (if 0 appointments)
    dl.add_transition_route(
        parent=get_all_appointments_call_webhook_task,
        transition=dl.create_transition_route(
            condition="$session.params.num_appointments = 0",
            target_page=end_human_escalation_page,
        ),
    )

    # extract the first appointment from the list of appointments
    extract_first_of_all_appointments_set_vars_task = dl.create_page(
        flow=find_existing_appointment_flow,
        page_name="- Extract 1st of All Appointments",
        entry_fulfillment=dl.create_fulfillment(
            set_parameter_actions=[
                dl.create_set_parameter_action(
                    parameter="first_appointment",
                    value="$sys.func.GET($session.params.appointments, 0)",
                ),
            ],
        ),
    )

    # get_all_appointments_call_webhook_task >>
    # extract_first_of_all_appointments_set_vars_task (when >= 1 appointment)
    dl.add_transition_route(
        parent=get_all_appointments_call_webhook_task,
        transition=dl.create_transition_route(
            condition="$session.params.num_appointments >= 1",
            target_page=extract_first_of_all_appointments_set_vars_task,
        ),
    )

    # describe a single appointment (one total or one for the first date)
    describe_single_appointment_page = dl.create_page(
        flow=find_existing_appointment_flow,
        page_name="> Describe 1 Appointment",
        entry_fulfillment=dl.create_fulfillment(
            messages=[
                dl.create_response_message(
                    text="""
Your next appointment is
$session.params.first_appointment.appointmentType
at
$session.params.first_appointment.facilityName.
It’s on
$sys.func.FORMAT_DATE($session.params.first_appointment.startTime,
"EEEE, MMMM dd")
at
$sys.func.FORMAT_DATE($session.params.first_appointment.startTime, "h:mm a").
""".replace(
                        "\n", " "
                    )
                ),
                dl.create_response_message(
                    "Is that the appointment you needed help with?"
                ),
            ],
        ),
    )

    # extract_first_of_all_appointments_set_vars_task >>
    # describe_single_appointment_page (when 1 appointment)
    dl.add_transition_route(
        parent=extract_first_of_all_appointments_set_vars_task,
        transition=dl.create_transition_route(
            condition="$session.params.num_appointments_on_date = 1",
            target_page=describe_single_appointment_page,
        ),
    )

    # describe_single_appointment_page >>
    # complete_with_first_appointment_set_var_task (when "yes")
    dl.add_transition_route(
        parent=describe_single_appointment_page,
        transition=dl.create_transition_route(
            intent=intent_yes,
            target_page=complete_with_first_appointment_set_var_task,
        ),
    )

    # describe_single_appointment_page >>
    # end_human_escalation_page (when "no" and only 1 appointment)
    dl.add_transition_route(
        parent=describe_single_appointment_page,
        transition=dl.create_transition_route(
            intent=intent_no,
            condition="$session.params.num_appointments = 1",
            target_page=end_human_escalation_page,
        ),
    )

    # extract the second appointment from the list of appointments
    extract_second_of_all_appointments_set_vars_task = dl.create_page(
        flow=find_existing_appointment_flow,
        page_name="- Extract 2nd of All Appointments",
        entry_fulfillment=dl.create_fulfillment(
            set_parameter_actions=[
                dl.create_set_parameter_action(
                    parameter="second_appointment",
                    value="$sys.func.GET($session.params.appointments, 1)",
                ),
            ],
        ),
    )

    # extract_first_of_all_appointments_set_vars_task >>
    # extract_second_of_all_appointments_set_vars_task (when >= 2 appointments)
    dl.add_transition_route(
        parent=extract_first_of_all_appointments_set_vars_task,
        transition=dl.create_transition_route(
            condition="$session.params.num_appointments_on_date >= 2",
            target_page=extract_second_of_all_appointments_set_vars_task,
        ),
    )

    # describe two appointments (two total or two for the first date)
    describe_two_appointments_page = dl.create_page(
        flow=find_existing_appointment_flow,
        page_name="> Describe 2 Appointments",
        entry_fulfillment=dl.create_fulfillment(
            messages=[
                dl.create_response_message(
                    text="""
Your next visit at
$session.params.first_appointment.facilityName,
it looks like you have 2 appointments.
$sys.func.FORMAT_DATE($session.params.first_appointment.startTime,
"EEEE, MMMM dd")
at $sys.func.FORMAT_DATE($session.params.first_appointment.startTime, "h:mm a")
with $session.params.first_appointment.doctorName and at
$sys.func.FORMAT_DATE($session.params.second_appointment.startTime, "h:mm a")
with $session.params.second_appointment.doctorName.
""".replace(
                        "\n", " "
                    )
                ),
                dl.create_response_message(
                    "Do you need help with one of those appointments?"
                ),
            ],
        ),
    )

    # extract_second_of_all_appointments_set_vars_task >>
    # describe_two_appointments_page (when 2 appointments)
    dl.add_transition_route(
        parent=extract_second_of_all_appointments_set_vars_task,
        transition=dl.create_transition_route(
            condition="$session.params.num_appointments_on_date = 2",
            target_page=describe_two_appointments_page,
        ),
    )

    # extract the third appointment from the list of appointments
    extract_third_of_all_appointments_set_vars_task = dl.create_page(
        flow=find_existing_appointment_flow,
        page_name="- Extract 3rd of All Appointments",
        entry_fulfillment=dl.create_fulfillment(
            set_parameter_actions=[
                dl.create_set_parameter_action(
                    parameter="third_appointment",
                    value="$sys.func.GET($session.params.appointments, 2)",
                ),
            ],
        ),
    )

    # extract_second_of_all_appointments_set_vars_task >>
    # extract_third_of_all_appointments_set_vars_task (when >= 3 appointments)
    dl.add_transition_route(
        parent=extract_second_of_all_appointments_set_vars_task,
        transition=dl.create_transition_route(
            condition="$session.params.num_appointments_on_date >= 3",
            target_page=extract_third_of_all_appointments_set_vars_task,
        ),
    )

    # describe three appointments (three total or three for the first date)
    describe_three_appointments_page = dl.create_page(
        flow=find_existing_appointment_flow,
        page_name="> Describe 3 Appointments",
        entry_fulfillment=dl.create_fulfillment(
            messages=[
                dl.create_response_message(
                    text="""
Your next visit at $session.params.first_appointment.facilityName,
it looks like you have 3 appointments.
$sys.func.FORMAT_DATE($session.params.first_appointment.startTime,
"EEEE, MMMM dd")
at $sys.func.FORMAT_DATE($session.params.first_appointment.startTime, "h:mm a")
with $session.params.first_appointment.doctorName, at
$sys.func.FORMAT_DATE($session.params.second_appointment.startTime, "h:mm a")
with $session.params.second_appointment.doctorName, and at
$sys.func.FORMAT_DATE($session.params.third_appointment.startTime, "h:mm a")
with $session.params.third_appointment.doctorName.
""".replace(
                        "\n", " "
                    )
                ),
                dl.create_response_message(
                    "Do you need help with one of those appointments?"
                ),
            ],
        ),
    )

    # extract_third_of_all_appointments_set_vars_task >>
    # describe_three_appointments_page (always)
    dl.add_transition_route(
        parent=extract_third_of_all_appointments_set_vars_task,
        transition=dl.create_transition_route(
            condition="true",
            target_page=describe_three_appointments_page,
        ),
    )

    # ask whether they know the provider of the appointment
    ask_if_patient_knows_provider_page = dl.create_page(
        flow=find_existing_appointment_flow,
        page_name="> Ask If Patient Knows Provider",
        entry_fulfillment=dl.create_fulfillment(
            messages=[
                dl.create_response_message(
                    text="Which provider is the appointment with?"
                ),
            ],
        ),
        form=dl.create_page_form(
            parameters=[
                dl.create_page_form_parameter(
                    name="provider_name",
                    entity_type=any_entity_type,
                    reprompt_event_handlers=[
                        *standard_match_event_handlers,
                    ],
                ),
            ]
        ),
        event_handlers=[
            *standard_match_event_handlers,
            dl.create_event_handler(
                # name="no-match-3",
                event="sys.no-match-3",
                target_page=end_human_escalation_page,
            ),
            dl.create_event_handler(
                # name="no-input-3",
                event="sys.no-input-3",
                target_page=end_human_escalation_page,
            ),
        ],
    )

    # ask_if_patient_knows_provider_page >>
    # end_human_escalation_page (when "no")
    dl.add_transition_route(
        parent=ask_if_patient_knows_provider_page,
        transition=dl.create_transition_route(
            intent=intent_no,
            target_page=end_human_escalation_page,
        ),
    )

    # ask_if_patient_knows_provider_page >>
    # end_human_escalation_page (when "help")
    dl.add_transition_route(
        parent=ask_if_patient_knows_provider_page,
        transition=dl.create_transition_route(
            intent=intent_agent_transfer,
            target_page=end_human_escalation_page,
        ),
    )
    time.sleep(5)

    # ask whether they know the date of the appointment
    ask_if_patient_knows_date_page = dl.create_page(
        flow=find_existing_appointment_flow,
        page_name="> Ask If Patient Knows Date",
        entry_fulfillment=dl.create_fulfillment(
            messages=[
                dl.create_response_message(
                    text="Do you know the date or week of the appointment?"
                ),
            ],
        ),
        form=dl.create_page_form(
            parameters=[
                dl.create_page_form_parameter(
                    name="appointment_date_obj",
                    entity_type=date_entity_type,
                    reprompt_event_handlers=[
                        *standard_match_event_handlers,
                    ],
                ),
            ]
        ),
        event_handlers=[
            *standard_match_event_handlers,
            dl.create_event_handler(
                # name="no-match-3",
                event="sys.no-match-3",
                target_page=ask_if_patient_knows_provider_page,
            ),
            dl.create_event_handler(
                # name="no-input-3",
                event="sys.no-input-3",
                target_page=ask_if_patient_knows_provider_page,
            ),
        ],
    )

    # describe_single_appointment_page >> ask_if_patient_knows_date_page
    # (when "no" and > 1 appointment)
    dl.add_transition_route(
        parent=describe_single_appointment_page,
        transition=dl.create_transition_route(
            intent=intent_no,
            condition="$session.params.num_appointments > 1",
            target_page=ask_if_patient_knows_date_page,
        ),
    )

    # describe_two_appointments_page >> end_human_escalation_page
    # (when "help")
    dl.add_transition_route(
        parent=describe_two_appointments_page,
        transition=dl.create_transition_route(
            intent=intent_agent_transfer,
            target_page=end_human_escalation_page,
        ),
    )

    # describe_two_appointments_page >> ask_if_patient_knows_date_page
    # (when "no" and > 2 appointment)
    dl.add_transition_route(
        parent=describe_two_appointments_page,
        transition=dl.create_transition_route(
            intent=intent_no,
            condition="$session.params.num_appointments > 2",
            target_page=ask_if_patient_knows_date_page,
        ),
    )

    # describe_two_appointments_page >> end_human_escalation_page
    # (when "no" and <= 2 appointment)
    dl.add_transition_route(
        parent=describe_two_appointments_page,
        transition=dl.create_transition_route(
            intent=intent_no,
            condition="$session.params.num_appointments <= 2",
            target_page=end_human_escalation_page,
        ),
    )

    # describe_three_appointments_page >> end_human_escalation_page
    # (when "help")
    dl.add_transition_route(
        parent=describe_three_appointments_page,
        transition=dl.create_transition_route(
            intent=intent_agent_transfer,
            target_page=end_human_escalation_page,
        ),
    )

    # describe_three_appointments_page >>
    # ask_if_patient_knows_date_page (when "no" and > 3 appointment)
    dl.add_transition_route(
        parent=describe_three_appointments_page,
        transition=dl.create_transition_route(
            intent=intent_no,
            condition="$session.params.num_appointments > 3",
            target_page=ask_if_patient_knows_date_page,
        ),
    )

    # describe_three_appointments_page >>
    # end_human_escalation_page (when "no" and <= 3 appointment)
    dl.add_transition_route(
        parent=describe_three_appointments_page,
        transition=dl.create_transition_route(
            intent=intent_no,
            condition="$session.params.num_appointments <= 3",
            target_page=end_human_escalation_page,
        ),
    )

    # extract appointment date from the form object
    extract_appointment_date_from_form_task = dl.create_page(
        flow=find_existing_appointment_flow,
        page_name="- Extract Appointment Date From Form",
        entry_fulfillment=dl.create_fulfillment(
            set_parameter_actions=[
                dl.create_set_parameter_action(
                    parameter="appointment_date",
                    value="""
$sys.func.CONCATENATE(
$sys.func.FORMAT_DATE($session.params.appointment_date_obj, "yyyy-MM-dd"),
"T00:00:00")
""".strip().replace(
                        "\n", " "
                    ),
                ),
            ],
        ),
    )

    # ask_if_patient_knows_date_page >>
    # extract_appointment_date_from_form_task (when form is filled)
    dl.add_transition_route(
        parent=ask_if_patient_knows_date_page,
        transition=dl.create_transition_route(
            condition='$page.params.status = "FINAL"',
            target_page=extract_appointment_date_from_form_task,
        ),
    )

    # ask_if_patient_knows_date_page >>
    # ask_if_patient_knows_provider_page (when "no")
    dl.add_transition_route(
        parent=ask_if_patient_knows_date_page,
        transition=dl.create_transition_route(
            intent=intent_no,
            target_page=ask_if_patient_knows_provider_page,
        ),
    )

    # ask_if_patient_knows_date_page >> end_human_escalation_page (when "help")
    dl.add_transition_route(
        parent=ask_if_patient_knows_date_page,
        transition=dl.create_transition_route(
            intent=intent_agent_transfer,
            target_page=end_human_escalation_page,
        ),
    )

    # ask for the time of the appointment
    ask_patient_for_time_page = dl.create_page(
        flow=find_existing_appointment_flow,
        page_name="> Ask Patient For Time",
        entry_fulfillment=dl.create_fulfillment(
            messages=[
                dl.create_response_message(
                    text="""
Ok, which appointment on
$sys.func.FORMAT_DATE($session.params.first_appointment.startTime, "MMMM dd")
do you need help with?
""".replace(
                        "\n", " "
                    )
                ),
            ],
        ),
        form=dl.create_page_form(
            parameters=[
                dl.create_page_form_parameter(
                    name="appointment_time_obj",
                    entity_type=time_entity_type,
                    reprompt_event_handlers=[
                        *standard_match_event_handlers,
                    ],
                ),
            ]
        ),
        event_handlers=[
            *standard_match_event_handlers,
            dl.create_event_handler(
                # name="no-match-3",
                event="sys.no-match-3",
                target_page=ask_if_patient_knows_provider_page,
            ),
            dl.create_event_handler(
                # name="no-input-3",
                event="sys.no-input-3",
                target_page=ask_if_patient_knows_provider_page,
            ),
        ],
    )
    time.sleep(5)

    # display_two_appointments_page >> ask_patient_for_time_page (when "yes")
    dl.add_transition_route(
        parent=describe_two_appointments_page,
        transition=dl.create_transition_route(
            intent=intent_yes,
            target_page=ask_patient_for_time_page,
        ),
    )
    time.sleep(5)

    # display_three_appointments_page >> ask_patient_for_time_page (when "yes")
    dl.add_transition_route(
        parent=describe_three_appointments_page,
        transition=dl.create_transition_route(
            intent=intent_yes,
            target_page=ask_patient_for_time_page,
        ),
    )
    time.sleep(5)

    # ask_patient_for_time_page >> end_human_escalation_page (when "help")
    dl.add_transition_route(
        parent=ask_patient_for_time_page,
        transition=dl.create_transition_route(
            intent=intent_agent_transfer,
            target_page=end_human_escalation_page,
        ),
    )
    time.sleep(5)

    # ask_patient_for_time_page >> ask_if_patient_knows_provider_page
    # (when "no")
    dl.add_transition_route(
        parent=ask_patient_for_time_page,
        transition=dl.create_transition_route(
            intent=intent_no,
            target_page=ask_if_patient_knows_provider_page,
        ),
    )

    # extract appointment time from the form object
    extract_appointment_time_from_form_task = dl.create_page(
        flow=find_existing_appointment_flow,
        page_name="- Extract Appointment Time From Form",
        entry_fulfillment=dl.create_fulfillment(
            set_parameter_actions=[
                dl.create_set_parameter_action(
                    parameter="appointment_date",
                    value="""
$sys.func.CONCATENATE(
$sys.func.FORMAT_DATE($session.params.first_appointment.startTime,
"yyyy-MM-dd"),
$sys.func.CONCATENATE(
"T",
$sys.func.FORMAT_DATE($session.params.appointment_time_obj, "HH:mm:ss")))
""".strip().replace(
                        "\n", " "
                    ),
                ),
            ],
        ),
    )
    time.sleep(5)

    # ask_patient_for_time_page >> extract_appointment_time_from_form_task
    # (when form is filled)
    dl.add_transition_route(
        parent=ask_patient_for_time_page,
        transition=dl.create_transition_route(
            condition='$page.params.status = "FINAL"',
            target_page=extract_appointment_time_from_form_task,
        ),
    )
    time.sleep(5)

    # fetch the first appointment after the provided date
    get_first_appointment_after_date_call_webhook_task = dl.create_page(
        flow=find_existing_appointment_flow,
        page_name="* Get the 1st Appointment After Date",
        entry_fulfillment=dl.create_fulfillment(
            webhook=get_appointments_webhook,
            tag="find_appointments",
            set_parameter_actions=[
                dl.create_set_parameter_action(
                    parameter="appointments_limit",
                    value=1,
                ),
            ],
        ),
        event_handlers=[
            dl.create_event_handler(
                # name="error",
                event="webhook.error",
                target_page=end_failure_page,
            ),
        ],
    )
    time.sleep(5)

    # extract_appointment_date_from_form_task >>
    # get_first_appointment_after_date_call_webhook_task (always)
    dl.add_transition_route(
        parent=extract_appointment_date_from_form_task,
        transition=dl.create_transition_route(
            condition="true",
            target_page=get_first_appointment_after_date_call_webhook_task,
        ),
    )
    time.sleep(5)

    # extract_appointment_time_from_form_task >>
    # get_first_appointment_after_date_call_webhook_task (always)
    dl.add_transition_route(
        parent=extract_appointment_time_from_form_task,
        transition=dl.create_transition_route(
            condition="true",
            target_page=get_first_appointment_after_date_call_webhook_task,
        ),
    )
    time.sleep(5)

    # extract the first appointment after the provided date
    extract_first_of_appointments_after_date_set_vars_task = dl.create_page(
        flow=find_existing_appointment_flow,
        page_name="- Extract 1st of Appointments After Date",
        entry_fulfillment=dl.create_fulfillment(
            set_parameter_actions=[
                dl.create_set_parameter_action(
                    parameter="first_appointment",
                    value="$sys.func.GET($session.params.appointments, 0)",
                ),
            ],
        ),
    )
    time.sleep(5)

    # get_first_appointment_after_date_call_webhook_task >>
    # extract_first_of_appointments_after_date_set_vars_task
    # (when >= 1 appointment)
    dl.add_transition_route(
        parent=get_first_appointment_after_date_call_webhook_task,
        transition=dl.create_transition_route(
            condition="$session.params.num_appointments >= 1",
            target_page=extract_first_of_appointments_after_date_set_vars_task,
        ),
    )
    time.sleep(5)

    # get_first_appointment_after_date_call_webhook_task >>
    # end_human_escalation_page (when 0 appointments)
    dl.add_transition_route(
        parent=get_first_appointment_after_date_call_webhook_task,
        transition=dl.create_transition_route(
            condition="$session.params.num_appointments = 0",
            target_page=end_human_escalation_page,
        ),
    )

    # display the first appointment after the provided date
    describe_first_appointment_after_date_page = dl.create_page(
        flow=find_existing_appointment_flow,
        page_name="> Describe 1st Appointment After Date",
        entry_fulfillment=dl.create_fulfillment(
            messages=[
                dl.create_response_message(
                    text="""
On
$sys.func.FORMAT_DATE($session.params.first_appointment.startTime,
"EEEE, MMMM dd")
at $sys.func.FORMAT_DATE($session.params.first_appointment.startTime, "h:mm a")
you're scheduled for
$session.params.first_appointment.appointmentType
with
$session.params.first_appointment.doctorName at
$session.params.first_appointment.facilityName.
""".replace(
                        "\n", " "
                    )
                ),
            ],
        ),
    )
    time.sleep(5)

    # extract_first_of_appointments_after_date_set_vars_task >>
    # describe_appointment_after_date_page (always)
    dl.add_transition_route(
        parent=extract_first_of_appointments_after_date_set_vars_task,
        transition=dl.create_transition_route(
            condition="true",
            target_page=describe_first_appointment_after_date_page,
        ),
    )
    time.sleep(5)

    # describe_first_appointment_after_date_page >>
    # complete_with_first_appointment_set_var_task (always)
    dl.add_transition_route(
        parent=describe_first_appointment_after_date_page,
        transition=dl.create_transition_route(
            condition="true",
            target_page=complete_with_first_appointment_set_var_task,
        ),
    )

    # fetch the next appointment with the provided provider
    get_next_appointment_with_provider_call_webhook_task = dl.create_page(
        flow=find_existing_appointment_flow,
        page_name="* Get the Next Appointment With Provider",
        entry_fulfillment=dl.create_fulfillment(
            webhook=get_appointments_webhook,
            tag="find_appointments",
            set_parameter_actions=[
                dl.create_set_parameter_action(
                    parameter="appointments_limit",
                    value=1,
                ),
            ],
        ),
        event_handlers=[
            dl.create_event_handler(
                name="error",
                event="webhook.error",
                target_page=end_failure_page,
            ),
        ],
    )
    time.sleep(5)

    # ask_if_patient_knows_provider_page >>
    # get_next_appointment_with_provider_call_webhook_task
    # (when form is filled)
    dl.add_transition_route(
        parent=ask_if_patient_knows_provider_page,
        transition=dl.create_transition_route(
            condition='$page.params.status = "FINAL"',
            target_page=get_next_appointment_with_provider_call_webhook_task,
        ),
    )
    time.sleep(5)

    # get_next_appointment_with_provider_call_webhook_task >>
    # end_human_escalation_page (when 0 appointments)
    dl.add_transition_route(
        parent=get_next_appointment_with_provider_call_webhook_task,
        transition=dl.create_transition_route(
            condition="$session.params.num_appointments = 0",
            target_page=end_human_escalation_page,
        ),
    )

    # extract the next appointment with the provided provider
    extract_next_appointment_with_provider_set_vars_task = dl.create_page(
        flow=find_existing_appointment_flow,
        page_name="- Extract Next Appointment With Provider",
        entry_fulfillment=dl.create_fulfillment(
            set_parameter_actions=[
                dl.create_set_parameter_action(
                    parameter="first_appointment",
                    value="$sys.func.GET($session.params.appointments, 0)",
                ),
            ],
        ),
    )
    time.sleep(5)

    # get_next_appointment_with_provider_call_webhook_task >>
    # extract_next_appointment_with_provider_set_vars_task
    # (when >= 1 appointment)
    dl.add_transition_route(
        parent=get_next_appointment_with_provider_call_webhook_task,
        transition=dl.create_transition_route(
            condition="$session.params.num_appointments >= 1",
            target_page=extract_next_appointment_with_provider_set_vars_task,
        ),
    )

    # display the next appointment with the provided provider
    describe_next_appointment_with_provider_page = dl.create_page(
        flow=find_existing_appointment_flow,
        page_name="> Describe Next Appointment With Provider",
        entry_fulfillment=dl.create_fulfillment(
            messages=[
                dl.create_response_message(
                    text="""
Your next visit with $session.params.first_appointment.doctorName
is
$session.params.first_appointment.appointmentType
on
$sys.func.FORMAT_DATE($session.params.first_appointment.startTime,
"EEEE, MMMM dd")
at $sys.func.FORMAT_DATE($session.params.first_appointment.startTime, "h:mm a")
at $session.params.first_appointment.facilityName.
""".replace(
                        "\n", " "
                    )
                ),
            ],
        ),
    )
    time.sleep(5)

    # extract_next_appointment_with_provider_set_vars_task >>
    # describe_next_appointment_with_provider_page (always)
    dl.add_transition_route(
        parent=extract_next_appointment_with_provider_set_vars_task,
        transition=dl.create_transition_route(
            condition="true",
            target_page=describe_next_appointment_with_provider_page,
        ),
    )
    time.sleep(5)

    # describe_next_appointment_with_provider_page >>
    # complete_with_first_appointment_set_var_task (always)
    dl.add_transition_route(
        parent=describe_next_appointment_with_provider_page,
        transition=dl.create_transition_route(
            condition="true",
            target_page=complete_with_first_appointment_set_var_task,
        ),
    )
    time.sleep(5)

    return find_existing_appointment_flow
