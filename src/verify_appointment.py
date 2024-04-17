import logging
from enum import Enum

from dfcx_scrapi.builders.routes import TransitionRouteBuilder
from dfcx_scrapi.core.flows import Flows

import utils
from utils import FlowNames, create_flow_by_name

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger()


class VerifyAppointmentPageNames(str, Enum):
    END_ESCALATION = "end escalation"
    COLLECT_APP_ID = "> collect app id"
    END_SUCCESS = "end success"


def create_verify_appointment_flow_pages(config):
    utils.create_fake_flow(
        config,
        FlowNames.ANYTHING_ELSE,
    )
    flows_instance = Flows()
    flow_name = FlowNames.VERIFY.value

    flow_obj, flows_instance, flows_map, pages_instance = create_flow_by_name(
        config=config, flow_name=flow_name, nlu_threshold=0.3
    )

    pages_to_create = [page.value for page in VerifyAppointmentPageNames]

    page_map, builder_map = utils.create_pages(
        pages_to_create, flow_obj, pages_instance, flows_map, flow_name
    )

    # create a transition from flow obj to Authentication
    # flow when $session.params.patientFound is null or "false"

    # authentication flow
    authentication_flow = flows_map[FlowNames.AUTHENTICATION]

    # create the transition for not authenticated
    not_auth_transition = TransitionRouteBuilder().create_new_proto_obj(
        condition="$session.params.patientFound = null"
        + ' OR $session.params.patientFound =  "false"',
        target_flow=authentication_flow,
    )
    # add the transition to the flow
    flow_obj.transition_routes.extend([not_auth_transition])

    # create the transition for authenticated direct to collect app id
    auth_transition = TransitionRouteBuilder().create_new_proto_obj(
        condition='$session.params.patientFound = "true"',
        target_page=page_map[VerifyAppointmentPageNames.COLLECT_APP_ID],
    )
    flow_obj.transition_routes.extend([auth_transition])

    # create the transition for  collect app id direct to find existing
    # appointment flow
    collect_app_id_transition = TransitionRouteBuilder().create_new_proto_obj(
        condition="$session.params.appointment_id = null",
        target_flow=flows_map[FlowNames.FIND_EXISTING_APPOINTMENT],
    )
    builder_map[
        VerifyAppointmentPageNames.COLLECT_APP_ID
    ].proto_obj.transition_routes.extend([collect_app_id_transition])

    appointment_found_fulfillment = utils.create_fulfillment_builder(
        parameter_presets={
            "denimSuccessfullyCompleted": "true",
        },
    ).proto_obj

    # create the transition for  after appointment is found
    appointment_found_transition = (
        TransitionRouteBuilder().create_new_proto_obj(
            trigger_fulfillment=appointment_found_fulfillment,
            condition="$session.params.appointment_id != null",
            target_flow=flows_map[FlowNames.ANYTHING_ELSE],
        )
    )

    builder_map[
        VerifyAppointmentPageNames.COLLECT_APP_ID
    ].proto_obj.transition_routes.extend([appointment_found_transition])

    # create symbolic transition for end success
    end_success_symbolic_transition = (
        TransitionRouteBuilder().create_new_proto_obj(
            condition="true",
            target_page=utils.get_symbolic_page(
                flow_obj.name, utils.SymbolicPages.END_FLOW
            ).name,
        )
    )

    # update the page
    builder_map[
        VerifyAppointmentPageNames.END_SUCCESS
    ].proto_obj.transition_routes.extend(
        [
            end_success_symbolic_transition,
        ]
    )

    # create symbolic transition for end escalation
    end_escalation_symbolic_transition = (
        TransitionRouteBuilder().create_new_proto_obj(
            condition="true",
            target_page=utils.get_symbolic_page(
                flow_obj.name,
                utils.SymbolicPages.END_FLOW_WITH_HUMAN_ESCALATION,
            ).name,
        )
    )
    # update the page
    builder_map[
        VerifyAppointmentPageNames.END_ESCALATION
    ].proto_obj.transition_routes.extend(
        [
            end_escalation_symbolic_transition,
        ]
    )
    # currently this states are not required
    event_handler_messages = utils.EventHandlerMessages(
        no_match_1="", no_match_2="", no_input_1="", no_input_2=""
    )
    event_handlers = utils.create_event_handlers(
        event_handler_messages,
        end_escalation_page=page_map[
            VerifyAppointmentPageNames.END_ESCALATION
        ],
    )
    flow_obj.event_handlers.extend(event_handlers)

    builder_map[
        VerifyAppointmentPageNames.COLLECT_APP_ID
    ].proto_obj.event_handlers.extend(event_handlers)
    utils.update_flow_and_pages(
        flow_obj=flow_obj,
        page_map=page_map,
        builder_map=builder_map,
        pages_instance=pages_instance,
        flows_instance=flows_instance,
    )
