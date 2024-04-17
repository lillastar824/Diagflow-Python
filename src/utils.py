import logging
import os
import time
from collections import defaultdict
from enum import Enum
from typing import Any, Dict, List, MutableSequence, TypedDict

import google.protobuf.duration_pb2 as duration_pb2  # type: ignore
from dfcx_scrapi.builders.flows import FlowBuilder
from dfcx_scrapi.builders.fulfillments import FulfillmentBuilder
from dfcx_scrapi.builders.intents import IntentBuilder
from dfcx_scrapi.builders.pages import PageBuilder
from dfcx_scrapi.builders.response_messages import ResponseMessageBuilder
from dfcx_scrapi.builders.routes import (  # noqa: E501
    EventHandlerBuilder,
    TransitionRouteBuilder,
)
from dfcx_scrapi.core.agents import Agents
from dfcx_scrapi.core.entity_types import EntityTypes
from dfcx_scrapi.core.flows import Flows
from dfcx_scrapi.core.intents import Intents
from dfcx_scrapi.core.pages import Pages
from dfcx_scrapi.core.webhooks import Webhooks
from dfcx_scrapi.tools.copy_util import CopyUtil
from google.api_core import exceptions as core_exceptions
from google.cloud.dialogflowcx_v3beta1.types import (  # noqa: E501
    EventHandler,
    NluSettings,
    Page,
    TransitionRoute,
    Webhook,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger()

DEFAULT_START_FLOW = "Default Start Flow"


class FlowNames(str, Enum):
    # ordering matters put the flow with no dependencies first
    # and the flow with the most dependencies last
    # if flow A depends on flow B, then A should be after B
    NAME_COLLECTION = "Name Collection"
    DOB_COLLECTION = "Dob Collection"
    SSN_COLLECTION = "SSN Collection"
    AUTHENTICATION = "Authentication"
    FIND_EXISTING_APPOINTMENT = "Find Existing Appointment"
    VERIFY = "Verify"
    CANCEL = "Cancel"
    RESCHEDULE = "Reschedule"
    CREATE_NEW_APPOINTMENT = "Create Appointment"
    SCHEDULING = "Scheduling"
    WRAPUP_BLOCK = "Wrapup Block"
    ANYTHING_ELSE = "Anything Else"
    OFFICE_HOURS = "Office Hours"


class WebHookNames(str, Enum):
    DIAGFLOW = "diagflow"
    UPSERT_DATA_INTO_SPANNER = "upsert-data-into-spanner"


class WebHookTags(str, Enum):
    Authentication = "authenticate"


def get_webhook_uri(webhook_name: WebHookNames):

    webhook_uri = {
        WebHookNames.DIAGFLOW: os.environ["DIAGFLOW_URL"],
        WebHookNames.UPSERT_DATA_INTO_SPANNER: os.environ[
            "UPSERT_DATA_INTO_SPANNER_URL"
        ],
    }
    if webhook_name not in webhook_uri:
        raise ValueError(f"Webhook {webhook_name} not found")
    return webhook_uri[webhook_name]


class IntentNames(str, Enum):
    APPOINTMENT_ROUTING_BILLING = "appointment.routing.billing"
    APPOINTMENT_ROUTING_CANCEL = "appointment.routing.cancel"
    APPOINTMENT_ROUTING_EXISTING = "appointment.routing.existing"
    APPOINTMENT_ROUTING_NEW_APP = "appointment.routing.new_app"
    APPOINTMENT_ROUTING_MEDICATION_REFILL = (
        "appointment.routing.medication_refill"
    )
    APPOINTMENT_ROUTING_RESCHEDULE = "appointment.routing.reschedule"
    WRAPUP_WAIT = "wrapup.wait"
    DEFAULT_WELCOME_INTENT = "Default Welcome Intent"
    PREBUILT_COMPONENTS_CONFIRMATION_NO = "prebuilt_components_confirmation_no"
    PREBUILT_COMPONENTS_CONFIRMATION_YES = (
        "prebuilt_components_confirmation_yes"
    )
    PREBUILT_COMPONENTS_ESCALATE_HUMAN_AGENT = (
        "prebuilt_components_escalate_human_agent"
    )


class IntentUserNames(str, Enum):
    APPOINTMENT_ROUTING_BILLING = "Caller is seeking information about billing"
    APPOINTMENT_ROUTING_CANCEL = "Caller is seeking to cancel an appointment"
    APPOINTMENT_ROUTING_EXISTING = (
        "Caller is seeking to verify an existing appointment"
    )
    APPOINTMENT_ROUTING_NEW_APP = (
        "Caller is seeking to create a new appointment"
    )
    APPOINTMENT_ROUTING_RESCHEDULE = (
        "Caller is seeking to reschedule an appointment"
    )
    PREBUILT_COMPONENTS_ESCALATE_HUMAN_AGENT = (
        "Caller is seeking to escalate to a human agent"
    )
    APPOINTMENT_ROUTING_MEDICATION_REFILL = (
        "Caller is seeking a medication refill"
    )


class EventNames(str, Enum):
    NO_INPUT_DEFAULT = "sys.no-input-default"
    NO_INPUT_1 = "sys.no-input-1"
    NO_INPUT_2 = "sys.no-input-2"
    NO_INPUT_3 = "sys.no-input-3"
    NO_MATCH_1 = "sys.no-match-1"
    NO_MATCH_2 = "sys.no-match-2"
    NO_MATCH_3 = "sys.no-match-3"
    FLOW_FAILED = "flow.failed"
    FLOW_FAILED_HUMAN_ESCALATION = "flow.failed.human-escalation"
    WEBHOOK_ERROR = "webhook.error"


class Config:
    def __init__(
        self,
    ):
        self.project_id = os.environ.get("PROJECT_ID")
        self.service_account_key = os.environ.get(
            "GOOGLE_APPLICATION_CREDENTIALS"
        )
        self.agent_display_name = os.environ.get("AGENT_DISPLAY_NAME")
        self.archieve_display_name = os.environ.get(
            "AGENT_DISPLAY_NAME_ARCHIEVE"
        )
        self.gcs_bucket_uri_to_restore = os.environ.get(
            "GCS_BUCKET_URI_TO_RESTORE"
        )


def delete_flow_with_check(flow_display_name, config, agent_id=None):
    if agent_id is None:
        agent_id = get_agent_id(config)
    flow_instance = Flows(creds_path=config.service_account_key)

    try:
        flow_obj = flow_instance.get_flow_by_display_name(
            flow_display_name, agent_id=agent_id
        )
        if flow_obj.name != "00000000-0000-0000-0000-000000000000":
            flow_instance.delete_flow(flow_obj.name, force=True)
    except ValueError as e:
        # means does not exist
        logger.debug(e)
    except Exception as e:
        logger.error(e)
        raise


def get_agent_id(config: Config):
    agents = Agents(creds_path=config.service_account_key)
    agent = agents.get_agent_by_display_name(
        project_id=config.project_id, display_name=config.agent_display_name
    )
    return agent.name


class SymbolicPages(str, Enum):
    END_FLOW_WITH_FAILURE = "END_FLOW_WITH_FAILURE"
    END_FLOW = "END_FLOW"
    END_FLOW_WITH_HUMAN_ESCALATION = "END_FLOW_WITH_HUMAN_ESCALATION"
    END_SESSION = "END_SESSION"


class EventHandlerMessages:
    def __init__(self, no_match_1, no_match_2, no_input_1, no_input_2):
        self.no_match_1 = no_match_1
        self.no_match_2 = no_match_2
        self.no_input_1 = no_input_1
        self.no_input_2 = no_input_2


def create_event_handlers(
    event_handler_messages: EventHandlerMessages,
    end_escalation_page: str,
    page_parameter: bool = False,
):
    def helper(event: str, message: List[str], escalate: bool):
        fulfilment_builder = FulfillmentBuilder()
        fulfilment_builder.create_new_proto_obj(overwrite=True)
        response_message = ResponseMessageBuilder().create_new_proto_obj(
            response_type="text",
            message=message,
        )
        if message:
            fulfilment_builder.add_response_message(response_message)

        # create no input event handler
        if not escalate:
            no_input_event_handler = (
                EventHandlerBuilder().create_new_proto_obj(
                    event=event,
                    trigger_fulfillment=fulfilment_builder.proto_obj,
                )
            )
        else:
            no_input_event_handler = (
                EventHandlerBuilder().create_new_proto_obj(
                    event=event,
                    trigger_fulfillment=fulfilment_builder.proto_obj,
                    target_page=end_escalation_page,
                )
            )
        return no_input_event_handler

    # create event handlers
    event_handlers = [
        helper(
            EventNames.NO_INPUT_1, event_handler_messages.no_input_1, False
        ),
        helper(
            EventNames.NO_INPUT_2, event_handler_messages.no_input_2, False
        ),
        helper(EventNames.NO_INPUT_3, [], True),
        helper(
            EventNames.NO_MATCH_1, event_handler_messages.no_match_1, False
        ),
        helper(
            EventNames.NO_MATCH_2, event_handler_messages.no_match_2, False
        ),
        helper(EventNames.NO_MATCH_3, [], True),
        helper(EventNames.FLOW_FAILED, [], True),
        helper(EventNames.FLOW_FAILED_HUMAN_ESCALATION, [], True),
        helper(EventNames.WEBHOOK_ERROR, [], True),
    ]
    if page_parameter:
        event_handlers = [
            helper(
                EventNames.NO_INPUT_1, event_handler_messages.no_input_1, False
            ),
            helper(
                EventNames.NO_INPUT_2, event_handler_messages.no_input_2, False
            ),
            helper(EventNames.NO_INPUT_3, [], True),
            helper(
                EventNames.NO_MATCH_1, event_handler_messages.no_match_1, False
            ),
            helper(
                EventNames.NO_MATCH_2, event_handler_messages.no_match_2, False
            ),
            helper(EventNames.NO_MATCH_3, [], True),
        ]
    return event_handlers


def get_symbolic_page(flow_name: str, mode: SymbolicPages):
    symbolic_dict = {
        SymbolicPages.END_FLOW_WITH_FAILURE: Page(
            name=f"{flow_name}/pages/END_FLOW_WITH_FAILURE"
        ),
        SymbolicPages.END_FLOW: Page(name=f"{flow_name}/pages/END_FLOW"),
        SymbolicPages.END_FLOW_WITH_HUMAN_ESCALATION: Page(
            name=f"{flow_name}/pages/END_FLOW_WITH_HUMAN_ESCALATION"
        ),
    }
    return symbolic_dict[mode]


def get_resource_objects(config, source_agent, destination_agent):
    flows = Flows(creds_path=config.service_account_key)
    flows.list_flows(source_agent)
    for loop_flow in [
        "Waiting Room",
        "Dob Collection",
        "SSN Collection",
    ]:
        # if "Default Start Flow" in loop_flow.display_name:
        #     continue
        copy_flow(config, source_agent, destination_agent, loop_flow)


def copy_flow(config, source_agent, destination_agent, flow_name):
    # create flows object
    flows = Flows(creds_path=config.service_account_key)
    time.sleep(90)

    delete_flow_with_check(flow_name, config, destination_agent)

    flow_builder = FlowBuilder().create_new_proto_obj(flow_name)
    flows.create_flow(obj=flow_builder, agent_id=destination_agent)

    cu_src = CopyUtil(
        creds_path=config.service_account_key, agent_id=source_agent
    )
    cu_dst = CopyUtil(
        creds_path=config.service_account_key, agent_id=destination_agent
    )
    flows_map_src = cu_src.flows.get_flows_map(source_agent, reverse=True)
    flows_map_dst = cu_dst.flows.get_flows_map(destination_agent, reverse=True)

    source_pages = cu_src.pages.list_pages(flows_map_src[flow_name])

    for page in source_pages:
        cu_dst.pages.create_page(
            flows_map_dst[flow_name], display_name=page.display_name
        )
    # Step 1
    pages_prepped = cu_src.convert_from_source_page_dependencies(
        source_agent, source_pages, flow_name
    )

    # Step 2
    final_pages = cu_dst.convert_to_destination_page_dependencies(
        destination_agent, pages_prepped, flow_name
    )

    for page in final_pages:
        print(page.name)
        time.sleep(3)

        cu_dst.pages.update_page(page.name, page)
        print("Updated Page: {}".format(page.display_name))

    # Get the source and target flow objects
    source_flow_obj = cu_src.flows.get_flow_by_display_name(
        flow_name, source_agent
    )

    # Convert resources of start page in source flow to update
    # start page in target flow
    converted_source = cu_src.convert_start_page_dependencies(
        source_agent, source_flow_obj, agent_type="source", flow=flow_name
    )

    print("original:", converted_source)
    time.sleep(60)

    converted_target = cu_dst.convert_start_page_dependencies(
        destination_agent,
        converted_source,
        agent_type="destination",
        flow=flow_name,
        source_agent=source_agent,
    )
    print("Converted:", converted_target)
    # Update start page in target flow
    time.sleep(60)
    cu_dst.flows.update_flow(converted_target.name, converted_target)
    print(f"Updated Flow: {flow_name}")


def copy_paste_from_archieve(config):
    destination_agent = get_agent_id(config)
    tmp = config.agent_display_name
    config.agent_display_name = config.archieve_display_name
    source_agent = get_agent_id(config)
    config.agent_display_name = tmp

    entities = EntityTypes(creds_path=config.service_account_key)
    intents = Intents(creds_path=config.service_account_key)
    webhooks = Webhooks(creds_path=config.service_account_key)
    resources_objects = defaultdict(list)
    skip_list = defaultdict(list)

    source_entities = entities.list_entity_types(source_agent)
    for entity in source_entities:
        resources_objects["entities"].append(entity)

    source_intents = intents.list_intents(source_agent)
    for intent in source_intents:
        if "Default Negative Intent" in intent.display_name:
            print(intent.display_name)
            continue
        if "Default Welcome Intent" in intent.display_name:
            print(intent.display_name)
            continue
        resources_objects["intents"].append(intent)

    source_webhooks = webhooks.list_webhooks(source_agent)
    for source_webhook in source_webhooks:
        resources_objects["webhooks"].append(source_webhook)

    copy_util = CopyUtil(
        creds_path=config.service_account_key, agent_id=destination_agent
    )

    copy_util._create_webhook_resources(
        destination_agent, resources_objects, skip_list
    )
    copy_util._create_entity_resources(
        destination_agent, resources_objects, skip_list
    )
    copy_util._create_intent_resources(
        source_agent, destination_agent, resources_objects, skip_list
    )

    get_resource_objects(config, source_agent, destination_agent)


def existing_transition_route(
    tr: TransitionRoute, ts_list: MutableSequence[TransitionRoute]
):
    return any(
        tr.intent == tr_item.intent
        and tr.target_page == tr_item.target_page
        and tr.condition == tr_item.condition
        and tr.target_page == tr_item.target_page
        for tr_item in ts_list
    )


def is_existing_event_handler(
    eh: EventHandler, eh_list: MutableSequence[EventHandler]
):
    return any(eh.event == eh_item.event for eh_item in eh_list)


class ResponseMessageArgs(TypedDict):
    type: str
    message: str | List[str] | Dict[str, Any] | Dict[str, str]


def create_fulfillment_builder(
    webhook: str = None,
    tag: str = None,
    parameter_presets: Dict[str, str] = None,
    response_message: ResponseMessageArgs = None,
) -> FulfillmentBuilder:
    fulfillment_builder = FulfillmentBuilder()
    fulfillment_builder.create_new_proto_obj(
        webhook=webhook,
        tag=tag,
    )
    if parameter_presets:
        fulfillment_builder.add_parameter_presets(parameter_presets)

    if response_message:
        response_message_obj = ResponseMessageBuilder().create_new_proto_obj(
            response_type=response_message["type"],
            message=response_message["message"],
        )
        fulfillment_builder.add_response_message(response_message_obj)

    return fulfillment_builder


def create_webhook(config: Config, webhook_obj: Webhook):
    agent_id = get_agent_id(config)
    webhooks_instance = Webhooks(agent_id=agent_id)
    try:
        webhooks_instance.get_webhook_by_display_name(webhook_obj.display_name)
    except ValueError:
        logger.info("Creating webhook %s ...", webhook_obj.display_name)
        webhooks_instance.create_webhook(agent_id=agent_id, obj=webhook_obj)
        pass
    except Exception as e:
        logger.error(e)
        raise


def create_intents(config, intent_items: dict[str, list[str]]):
    agent_id = get_agent_id(config)
    intents = Intents()
    for display_name, intent_list in intent_items.items():
        intent_obj = IntentBuilder().create_new_proto_obj(
            display_name=display_name,
        )
        training_phrases = []
        for text in intent_list:
            phrase = intent_obj.TrainingPhrase()
            phrase.repeat_count = 1
            phrase.parts.extend([phrase.Part(text=text)])
            training_phrases.append(phrase)

        intent_obj.training_phrases.extend(training_phrases)
        try:
            intents.create_intent(agent_id=agent_id, obj=intent_obj)
        except core_exceptions.AlreadyExists as error:
            logger.info(error)


def create_event_handler(
    event: str,
    message: str = None,
    target_page: str = None,
):
    fulfilment_builder = FulfillmentBuilder()
    fulfilment_builder.create_new_proto_obj(overwrite=True)
    if message:
        response_message = ResponseMessageBuilder().create_new_proto_obj(
            response_type="text",
            message=message,
        )
        fulfilment_builder.add_response_message(response_message)

    if target_page is None:
        no_input_event_handler = EventHandlerBuilder().create_new_proto_obj(
            event=event,
            trigger_fulfillment=fulfilment_builder.proto_obj,
        )
    else:
        no_input_event_handler = EventHandlerBuilder().create_new_proto_obj(
            event=event,
            trigger_fulfillment=fulfilment_builder.proto_obj,
            target_page=target_page,
        )
    return no_input_event_handler


def create_fake_flow(config, flow_name, flow_text: str = None):
    agent_id = get_agent_id(config)
    flows_instance = Flows()
    flow_obj = FlowBuilder().create_new_proto_obj(
        display_name=flow_name,
    )
    flow_obj = flows_instance.create_flow(agent_id=agent_id, obj=flow_obj)

    fulfilment_builder = FulfillmentBuilder()
    fulfilment_builder.create_new_proto_obj()

    if flow_text:
        response_message = ResponseMessageBuilder().create_new_proto_obj(
            response_type="text", message=flow_text
        )
        fulfilment_builder.add_response_message(response_message)

    end_success_symbolic_transition = (
        TransitionRouteBuilder().create_new_proto_obj(
            condition="true",
            trigger_fulfillment=fulfilment_builder.proto_obj,
            target_page=get_symbolic_page(
                flow_obj.name, SymbolicPages.END_FLOW
            ).name,
        )
    )
    flow_obj.transition_routes.extend([end_success_symbolic_transition])
    return flows_instance.update_flow(flow_id=flow_obj.name, obj=flow_obj)


def set_flow_nlu_settings(flow_obj, threshold=0.3):
    flow_obj.nlu_settings.classification_threshold = threshold
    flow_obj.nlu_settings.model_type = (
        NluSettings.ModelType.MODEL_TYPE_ADVANCED
    )
    return flow_obj


def create_flow_by_name(config, flow_name, nlu_threshold=0.3):
    agent_id = get_agent_id(config)
    delete_flow_with_check(flow_display_name=flow_name, config=config)
    flow_obj_proto = FlowBuilder().create_new_proto_obj(
        display_name=flow_name,
    )
    set_flow_nlu_settings(flow_obj_proto, threshold=nlu_threshold)
    flow_obj = Flows().create_flow(agent_id=agent_id, obj=flow_obj_proto)
    flows_instance = Flows()
    flows_map = flows_instance.get_flows_map(agent_id=agent_id, reverse=True)
    pages_instance = Pages(creds_path=config.service_account_key)
    return flow_obj, flows_instance, flows_map, pages_instance


def create_pages(
    pages_to_create, flow_obj, pages_instance, flows_map, flow_name
):

    builder_map = {}
    for page in pages_to_create:
        page_builder = PageBuilder()
        page_builder.create_new_proto_obj(display_name=page, overwrite=True)
        builder_map[page] = page_builder
    for page_display_name, builder in builder_map.items():
        pages_instance.create_page(
            obj=builder.proto_obj, flow_id=flow_obj.name
        )

    page_map = pages_instance.get_pages_map(flows_map[flow_name], reverse=True)

    return page_map, builder_map


def update_flow_and_pages(
    builder_map, pages_instance, flows_instance, flow_obj, page_map
):
    for page_display_name, builder in builder_map.items():
        pages_instance.update_page(
            page_id=page_map[page_display_name], obj=builder.proto_obj
        )

    # update flow
    flows_instance.update_flow(flow_id=flow_obj.name, obj=flow_obj)


def create_webhook_if_not_exists(config, wb_name, uri):
    agent_id = get_agent_id(config)
    webhooks_instance = Webhooks(agent_id=agent_id)

    try:
        wh_map = webhooks_instance.get_webhooks_map(
            agent_id=agent_id, reverse=True
        )
        wb_id = wh_map[wb_name]
        webhook_obj = webhooks_instance.get_webhook(wb_id)
        webhook_obj.generic_web_service.uri = uri
        webhooks_instance.update_webhook(
            webhook_id=wb_id, webhook_obj=webhook_obj
        )
    except KeyError:
        logger.info("Creating webhook %s ...", wb_name)
        webhook_obj = Webhook()
        webhook_obj.display_name = wb_name
        webhook_obj.generic_web_service.uri = uri
        timeout_duration = duration_pb2.Duration()
        timeout_duration.seconds = 10  # Set the timeout to 10 seconds
        webhook_obj.timeout = timeout_duration
        webhooks_instance.create_webhook(agent_id=agent_id, obj=webhook_obj)
    except Exception as e:
        logger.error(e)
        raise
