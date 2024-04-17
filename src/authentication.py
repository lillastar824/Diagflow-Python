import logging
from enum import Enum

from dfcx_scrapi.builders.flows import FlowBuilder
from dfcx_scrapi.builders.fulfillments import FulfillmentBuilder
from dfcx_scrapi.builders.pages import PageBuilder
from dfcx_scrapi.builders.response_messages import ResponseMessageBuilder
from dfcx_scrapi.builders.routes import TransitionRouteBuilder
from dfcx_scrapi.core.flows import Flows
from dfcx_scrapi.core.intents import Intents
from dfcx_scrapi.core.pages import Pages
from dfcx_scrapi.core.webhooks import Webhooks

import commons
import utils
from utils import FlowNames, create_webhook_if_not_exists

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger()


class AuthPageNames(str, Enum):
    END_SUCCESS = "end success"
    END_ESCALATION = "end escalation"
    COLLECT_DOB = "> collect dob"
    COLLECT_NAME = "> collect name"
    COLLECT_SSN = "> collect ssn"
    AUTH_DOB_NAME = "# auth dob name"
    AUTH_DOB_NAME_SSN = "# auth dob name ssn"


class NamePageNames(str, Enum):
    END_SUCCESS = "end success"
    END_ESCALATION = "end escalation"
    COLLECT_NAME = "> collect name"


def create_name_collection_flow_pages(config):
    agent_id = utils.get_agent_id(config)
    flows_instance = Flows()
    flow_name = FlowNames.NAME_COLLECTION

    utils.delete_flow_with_check(flow_display_name=flow_name, config=config)
    # nc stands for name collection
    # fb stands for flow builder
    nc_fb = FlowBuilder().create_new_proto_obj(flow_name)
    nc_flow = flows_instance.create_flow(obj=nc_fb, agent_id=agent_id)

    pages_instance = Pages(creds_path=config.service_account_key)
    pages_to_create = [page.value for page in NamePageNames]

    builder_map = {}
    for page in pages_to_create:
        page_builder = PageBuilder()
        page_builder.create_new_proto_obj(display_name=page, overwrite=True)
        builder_map[page] = page_builder
    for page_display_name, builder in builder_map.items():
        pages_instance.create_page(obj=builder.proto_obj, flow_id=nc_flow.name)
    flows_map = flows_instance.get_flows_map(agent_id=agent_id, reverse=True)
    page_map = pages_instance.get_pages_map(
        flows_map[FlowNames.NAME_COLLECTION], reverse=True
    )

    # create transitions
    collect_name_transition = TransitionRouteBuilder().create_new_proto_obj(
        condition="true",
        target_page=page_map[NamePageNames.COLLECT_NAME],
    )

    nc_flow.transition_routes.extend([collect_name_transition])

    collect_name_page_builder: PageBuilder = builder_map[
        NamePageNames.COLLECT_NAME
    ]

    fulfilment_form_builder = FulfillmentBuilder()
    fulfilment_form_builder.create_new_proto_obj()
    response_message = ResponseMessageBuilder().create_new_proto_obj(
        response_type="text", message=commons.COLLECT_NAME_PROMPT
    )
    fulfilment_form_builder.add_response_message(response_message)
    # entityTypes_instance = EntityTypes(creds_path=config.service_account_key)
    # entities_map = entityTypes_instance.get_entities_map(
    #     agent_id=agent_id, reverse=True
    # )

    reprompt_messages = utils.EventHandlerMessages(
        no_match_1=commons.NAME_NO_MATCH_1,
        no_match_2=commons.NAME_NO_MATCH_2,
        no_input_1=commons.NAME_NO_INPUT_1,
        no_input_2=commons.NAME_NO_INPUT_2,
    )
    reprompt_event_handlers = utils.create_event_handlers(
        reprompt_messages,
        end_escalation_page=page_map[NamePageNames.END_ESCALATION],
        page_parameter=True,
    )
    print(reprompt_event_handlers)

    sys_any = "projects/-/locations/-/agents/-/entityTypes/sys.any"
    collect_name_page_builder.add_parameter(
        display_name="name",
        entity_type=sys_any,
        required=True,
        initial_prompt_fulfillment=fulfilment_form_builder.proto_obj,
        reprompt_event_handlers=reprompt_event_handlers,
    )

    params_are_set_tr = TransitionRouteBuilder().create_new_proto_obj(
        condition='$page.params.status = "FINAL"',
        target_page=page_map[NamePageNames.END_SUCCESS],
        trigger_fulfillment=utils.create_fulfillment_builder(
            response_message={
                "message": commons.COLLECT_NAME_OK,
                "type": "text",
            },
        ).proto_obj,
    )
    intents_instance = Intents()
    intents_map = intents_instance.get_intents_map(
        agent_id=agent_id, reverse=True
    )
    human_escalation_tr = TransitionRouteBuilder().create_new_proto_obj(
        intent=intents_map[
            utils.IntentNames.PREBUILT_COMPONENTS_ESCALATE_HUMAN_AGENT
        ],
        target_page=page_map[NamePageNames.END_ESCALATION],
    )

    builder_map[NamePageNames.COLLECT_NAME].proto_obj.transition_routes.extend(
        [
            human_escalation_tr,
            params_are_set_tr,
        ]
    )

    event_handler_messages = utils.EventHandlerMessages(
        no_match_1=commons.NAME_NO_MATCH_1,
        no_match_2=commons.NAME_NO_MATCH_2,
        no_input_1=commons.NAME_NO_INPUT_1,
        no_input_2=commons.NAME_NO_INPUT_2,
    )
    event_handlers = utils.create_event_handlers(
        event_handler_messages,
        end_escalation_page=page_map[NamePageNames.END_ESCALATION],
    )

    end_success_symbolic_transition = (
        TransitionRouteBuilder().create_new_proto_obj(
            condition="true",
            target_page=utils.get_symbolic_page(
                nc_flow.name, utils.SymbolicPages.END_FLOW
            ).name,
        )
    )
    builder_map[NamePageNames.END_SUCCESS].proto_obj.transition_routes.extend(
        [
            end_success_symbolic_transition,
        ]
    )

    end_escalation_symbolic_transition = (
        TransitionRouteBuilder().create_new_proto_obj(
            condition="true",
            target_page=utils.get_symbolic_page(
                nc_flow.name,
                utils.SymbolicPages.END_FLOW_WITH_HUMAN_ESCALATION,
            ).name,
        )
    )
    builder_map[
        NamePageNames.END_ESCALATION
    ].proto_obj.transition_routes.extend(
        [
            end_escalation_symbolic_transition,
        ]
    )

    for page_display_name, builder in builder_map.items():
        print(page_map[page_display_name])
        print("-" * 100)
        print("\n\n")
        if page_display_name not in [
            NamePageNames.END_ESCALATION,
            NamePageNames.END_SUCCESS,
        ]:
            builder.add_event_handler(event_handlers)

        pages_instance.update_page(
            page_id=page_map[page_display_name], obj=builder.proto_obj
        )

    flows_instance.update_flow(flow_id=nc_flow.name, obj=nc_flow)


def create_authentication_flow_pages(config):
    agent_id = utils.get_agent_id(config)
    flows_instance = Flows()
    flow_name = FlowNames.AUTHENTICATION
    utils.delete_flow_with_check(flow_display_name=flow_name, config=config)

    (
        authentication_flow,
        flows_instance,
        flows_map,
        pages_instance,
    ) = utils.create_flow_by_name(
        config=config, flow_name=flow_name, nlu_threshold=0.3
    )

    pages_to_create = [page.value for page in AuthPageNames]

    page_map, builder_map = utils.create_pages(
        pages_to_create=pages_to_create,
        flow_obj=authentication_flow,
        pages_instance=pages_instance,
        flows_map=flows_map,
        flow_name=flow_name,
    )

    # create transitions
    collect_dob_transition = TransitionRouteBuilder().create_new_proto_obj(
        condition="true",
        target_page=page_map[AuthPageNames.COLLECT_DOB],
    )
    authentication_flow.transition_routes.extend([collect_dob_transition])

    collect_dob_before_transition = (
        TransitionRouteBuilder().create_new_proto_obj(
            condition="$session.params.dob_collection_dob = null",
            target_flow=flows_map[FlowNames.DOB_COLLECTION],
        )
    )
    collect_after_before_transition = (
        TransitionRouteBuilder().create_new_proto_obj(
            condition="$session.params.dob_collection_dob != null",
            target_page=page_map[AuthPageNames.COLLECT_NAME],
        )
    )
    builder_map[AuthPageNames.COLLECT_DOB].proto_obj.transition_routes.extend(
        [collect_dob_before_transition, collect_after_before_transition]
    )

    collect_name_before_transition = (
        TransitionRouteBuilder().create_new_proto_obj(
            condition="$session.params.name = null",
            target_flow=flows_map[FlowNames.NAME_COLLECTION],
        )
    )
    collect_name_after_transition = (
        TransitionRouteBuilder().create_new_proto_obj(
            condition="$session.params.name != null",
            target_page=page_map[AuthPageNames.AUTH_DOB_NAME],
        )
    )

    builder_map[AuthPageNames.COLLECT_NAME].proto_obj.transition_routes.extend(
        [collect_name_before_transition, collect_name_after_transition]
    )
    webhooks_instance = Webhooks(agent_id=agent_id)
    diagflow_wh_enum = utils.WebHookNames.DIAGFLOW
    create_webhook_if_not_exists(
        config,
        diagflow_wh_enum.value,
        utils.get_webhook_uri(diagflow_wh_enum),  # noqa: E501
    )
    webhook_map = webhooks_instance.get_webhooks_map(reverse=True)
    logger.info("webhook_map: %s", webhook_map)
    webhook_dob_name_query_transition_fulfillment = (
        FulfillmentBuilder().create_new_proto_obj(
            webhook=webhook_map[diagflow_wh_enum.value],
            tag=utils.WebHookTags.Authentication,
        )
    )

    # Find Patient with Name and DOB Starts #####

    # Search for patient
    wh_dob_name_query_tr = TransitionRouteBuilder().create_new_proto_obj(
        condition="$session.params.patientFound = null",
        trigger_fulfillment=webhook_dob_name_query_transition_fulfillment,
    )

    # Patient found
    wh_dob_name_patient_found_tr = (
        TransitionRouteBuilder().create_new_proto_obj(
            condition='$session.params.patientFound = "true"',
            target_page=page_map[AuthPageNames.END_SUCCESS],
        )
    )
    wh_dob_name_patient_need_ssn_tr = (
        TransitionRouteBuilder().create_new_proto_obj(
            condition='$session.params.needToAskSsn = "true"'
            + " OR $session.params.patientFound = null",
            target_page=page_map[AuthPageNames.COLLECT_SSN],
        )
    )
    wh_dob_name_patient_failed_tr = (
        TransitionRouteBuilder().create_new_proto_obj(
            condition='$session.params.needToAskSsn = "false"',
            target_page=page_map[AuthPageNames.END_ESCALATION],
        )
    )

    translation_routes = [
        wh_dob_name_query_tr,
        wh_dob_name_patient_found_tr,
        wh_dob_name_patient_need_ssn_tr,
        wh_dob_name_patient_failed_tr,
    ]
    builder_map[
        AuthPageNames.AUTH_DOB_NAME
    ].proto_obj.transition_routes.extend(translation_routes)

    # Find Patient with Name and DOB Ends #####

    # Find Patient with Name, DOB and SSN Starts #####
    wh_dob_name_ssn_query_tr = TransitionRouteBuilder().create_new_proto_obj(
        condition="$session.params.patientFound = null"
        + ' OR $session.params.patientFound = "false"',
        trigger_fulfillment=webhook_dob_name_query_transition_fulfillment,
    )
    wh_dob_name_ssn_patient_found_tr = (
        TransitionRouteBuilder().create_new_proto_obj(
            condition='$session.params.patientFound = "true"',
            target_page=page_map[AuthPageNames.END_SUCCESS],
        )
    )
    wh_dob_name_ssn_patient_failed_tr = (
        TransitionRouteBuilder().create_new_proto_obj(
            condition='$session.params.patientFound = "false"',
            target_page=page_map[AuthPageNames.END_ESCALATION],
        )
    )
    translation_routes = [
        wh_dob_name_ssn_query_tr,
        wh_dob_name_ssn_patient_found_tr,
        wh_dob_name_ssn_patient_failed_tr,
    ]
    builder_map[
        AuthPageNames.AUTH_DOB_NAME_SSN
    ].proto_obj.transition_routes.extend(translation_routes)

    # Find Patient with Name, DOB and SSN Ends #####

    #############################################
    # create transition for collect ssn page similar to collect name page
    collect_ssn_before_transition = (
        TransitionRouteBuilder().create_new_proto_obj(
            condition="$session.params.ssn = null",
            target_flow=flows_map["SSN Collection"],
        )
    )
    collect_ssn_after_transition = (
        TransitionRouteBuilder().create_new_proto_obj(
            condition="$session.params.ssn != null",
            target_page=page_map[AuthPageNames.AUTH_DOB_NAME_SSN],
        )
    )
    builder_map[AuthPageNames.COLLECT_SSN].proto_obj.transition_routes.extend(
        [collect_ssn_before_transition, collect_ssn_after_transition]
    )

    end_success_symbolic_transition = (
        TransitionRouteBuilder().create_new_proto_obj(
            condition="true",
            target_page=utils.get_symbolic_page(
                authentication_flow.name, utils.SymbolicPages.END_FLOW
            ).name,
            trigger_fulfillment=utils.create_fulfillment_builder(
                response_message={
                    "message": (
                        "Thank you $sys.func.GET($sys.func.SPLIT("
                        '$session.params.genesysPatientName, " "),0).'
                    ),
                    "type": "text",
                },
            ).proto_obj,
        )
    )

    builder_map[AuthPageNames.END_SUCCESS].proto_obj.transition_routes.extend(
        [
            end_success_symbolic_transition,
        ]
    )

    end_escalation_symbolic_transition = (
        TransitionRouteBuilder().create_new_proto_obj(
            condition="true",
            target_page=utils.get_symbolic_page(
                authentication_flow.name,
                utils.SymbolicPages.END_FLOW_WITH_HUMAN_ESCALATION,
            ).name,
        )
    )
    builder_map[
        AuthPageNames.END_ESCALATION
    ].proto_obj.transition_routes.extend(
        [
            end_escalation_symbolic_transition,
        ]
    )
    event_handler_messages = utils.EventHandlerMessages(
        no_match_1=commons.AUTHENTICATION_NO_MATCH_1,
        no_match_2=commons.AUTHENTICATION_NO_MATCH_2,
        no_input_1=commons.AUTHENTICATION_NO_INPUT_1,
        no_input_2=commons.AUTHENTICATION_NO_INPUT_2,
    )
    event_handlers = utils.create_event_handlers(
        event_handler_messages,
        end_escalation_page=page_map[AuthPageNames.END_ESCALATION],
    )

    for page_display_name, builder in builder_map.items():
        print(page_map[page_display_name])
        print("-" * 100)
        print("\n\n")
        if page_display_name not in [
            AuthPageNames.END_ESCALATION,
            AuthPageNames.END_SUCCESS,
        ]:
            builder.add_event_handler(event_handlers)

        pages_instance.update_page(
            page_id=page_map[page_display_name], obj=builder.proto_obj
        )

    flows_instance.update_flow(
        flow_id=authentication_flow.name, obj=authentication_flow
    )
