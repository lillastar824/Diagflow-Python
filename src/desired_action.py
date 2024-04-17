import logging
from enum import Enum

from dfcx_scrapi.builders.flows import FlowBuilder
from dfcx_scrapi.builders.fulfillments import FulfillmentBuilder
from dfcx_scrapi.builders.response_messages import ResponseMessageBuilder
from dfcx_scrapi.builders.routes import TransitionRouteBuilder
from dfcx_scrapi.core.flows import Flows
from dfcx_scrapi.core.intents import Intents
from dfcx_scrapi.core.pages import Pages

import commons
import utils
from utils import FlowNames

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger()


class DesiredActionPageNames(str, Enum):
    END_ESCALATION = "end escalation"


def create_fake_flow(config, flow_name, flow_text):
    agent_id = utils.get_agent_id(config)
    flows_instance = Flows()
    flow_obj = FlowBuilder().create_new_proto_obj(
        display_name=flow_name,
    )
    flow_obj = flows_instance.create_flow(agent_id=agent_id, obj=flow_obj)

    fulfilment_builder = FulfillmentBuilder()
    fulfilment_builder.create_new_proto_obj()
    response_message = ResponseMessageBuilder().create_new_proto_obj(
        response_type="text", message=flow_text
    )
    fulfilment_builder.add_response_message(response_message)

    end_success_symbolic_transition = (
        TransitionRouteBuilder().create_new_proto_obj(
            condition="true",
            trigger_fulfillment=fulfilment_builder.proto_obj,
            target_page=utils.get_symbolic_page(
                flow_obj.name, utils.SymbolicPages.END_FLOW
            ).name,
        )
    )
    flow_obj.transition_routes.extend([end_success_symbolic_transition])
    flows_instance.update_flow(flow_id=flow_obj.name, obj=flow_obj)


class IntentTransition:
    _intent_map: dict | None = None
    _flows_map: dict | None = None
    _pages_map: dict | None = None
    _config = None
    _agent_id: str | None = None

    def __init__(
        self,
        *,
        intent_name,
        target_flow_name=None,
        target_page_name=None,
        head_intent=None,
        is_page=False,
    ):
        self.intent_name = intent_name
        self.target_flow_name = target_flow_name
        self.target_page_name = target_page_name
        self.head_intent = head_intent
        self.is_page = is_page

    @classmethod
    def get_config(cls):
        if cls._config is None:
            config = utils.Config()
            cls._config = config
        return cls._config

    @classmethod
    def get_agent_id(cls):
        config = cls.get_config()
        if cls._agent_id is None:
            agent_id = utils.get_agent_id(config)
            cls._agent_id = agent_id
        return cls._agent_id

    @classmethod
    def get_pages_map(cls):
        if cls._pages_map is None:
            config = cls.get_config()
            pages_instance = Pages(creds_path=config.service_account_key)
            scheduling_flow = cls.get_flows_map()[FlowNames.SCHEDULING]
            page_map = pages_instance.get_pages_map(
                scheduling_flow, reverse=True
            )
            cls._pages_map = page_map
        return cls._pages_map

    @classmethod
    def get_flows_map(cls):
        if cls._flows_map is None:
            flows_instance = Flows()
            flows_map = flows_instance.get_flows_map(
                agent_id=cls.get_agent_id(), reverse=True
            )
            cls._flows_map = flows_map
        return cls._flows_map

    @classmethod
    def get_intent_map(cls):
        if cls._intent_map is None:

            intents_instance = Intents()
            intents_map = intents_instance.get_intents_map(
                agent_id=cls.get_agent_id(), reverse=True
            )
            cls._intent_map = intents_map
        return cls._intent_map

    @property
    def intent(self):
        intent_map = self.get_intent_map()
        return intent_map[self.intent_name]

    @property
    def target_flow(self):
        flows_map = self.get_flows_map()
        return flows_map[self.target_flow_name]

    @property
    def target_page(self):
        pages_map = self.get_pages_map()
        return pages_map[self.target_page_name]

    @property
    def fullfilment(self):
        response_message = None
        if self.intent_name in commons.DESIRED_ACTION_PROMPT:
            response_message = {
                "message": commons.DESIRED_ACTION_PROMPT[self.intent_name],
                "type": "text",
            }
        return utils.create_fulfillment_builder(
            parameter_presets={
                "head_intent": self.head_intent,
            },
            response_message=response_message,
        ).proto_obj

    @property
    def transition(self):
        if self.is_page:
            transition_builder = TransitionRouteBuilder().create_new_proto_obj(
                trigger_fulfillment=self.fullfilment,
                intent=self.intent,
                target_page=self.target_page,
            )
        else:
            transition_builder = TransitionRouteBuilder().create_new_proto_obj(
                trigger_fulfillment=self.fullfilment,
                intent=self.intent,
                target_flow=self.target_flow,
            )
        return transition_builder


def create_desired_action_flow_pages(config):
    # create_intents(config)
    routes = [
        IntentTransition(
            intent_name=utils.IntentNames.APPOINTMENT_ROUTING_RESCHEDULE.value,
            target_flow_name=FlowNames.RESCHEDULE.value,
            head_intent=utils.IntentUserNames.APPOINTMENT_ROUTING_RESCHEDULE.value,  # noqa: E501
            is_page=False,
        ),
        IntentTransition(
            intent_name=utils.IntentNames.APPOINTMENT_ROUTING_CANCEL.value,
            target_flow_name=FlowNames.CANCEL.value,
            head_intent=utils.IntentUserNames.APPOINTMENT_ROUTING_CANCEL.value,
            is_page=False,
        ),
        IntentTransition(
            intent_name=utils.IntentNames.APPOINTMENT_ROUTING_NEW_APP.value,
            target_flow_name=FlowNames.CREATE_NEW_APPOINTMENT.value,
            head_intent=utils.IntentUserNames.APPOINTMENT_ROUTING_NEW_APP.value,  # noqa: E501
            is_page=False,
        ),
        IntentTransition(
            intent_name=utils.IntentNames.APPOINTMENT_ROUTING_EXISTING.value,
            target_flow_name=FlowNames.VERIFY.value,
            head_intent=utils.IntentUserNames.APPOINTMENT_ROUTING_EXISTING.value,  # noqa: E501
            is_page=False,
        ),
        IntentTransition(
            intent_name=utils.IntentNames.APPOINTMENT_ROUTING_BILLING.value,
            target_page_name=DesiredActionPageNames.END_ESCALATION.value,
            head_intent=utils.IntentUserNames.APPOINTMENT_ROUTING_BILLING.value,  # noqa: E501
            is_page=True,
        ),
        IntentTransition(
            intent_name=utils.IntentNames.APPOINTMENT_ROUTING_MEDICATION_REFILL.value,  # noqa: E501
            target_page_name=DesiredActionPageNames.END_ESCALATION.value,
            head_intent=utils.IntentUserNames.APPOINTMENT_ROUTING_MEDICATION_REFILL.value,  # noqa: E501
            is_page=True,
        ),
        IntentTransition(
            intent_name=utils.IntentNames.PREBUILT_COMPONENTS_ESCALATE_HUMAN_AGENT.value,  # noqa: E501
            target_page_name=DesiredActionPageNames.END_ESCALATION,
            head_intent=utils.IntentUserNames.PREBUILT_COMPONENTS_ESCALATE_HUMAN_AGENT.value,  # noqa: E501
            is_page=True,
        ),
    ]
    # create schedule appointment flow
    flow_name = FlowNames.SCHEDULING.value
    (
        flow_obj,
        flows_instance,
        flows_map,
        pages_instance,
    ) = utils.create_flow_by_name(
        config=config, flow_name=flow_name, nlu_threshold=0.5
    )
    pages_to_create = [page.value for page in DesiredActionPageNames]

    # delete scheduling flow if exists
    page_map, builder_map = utils.create_pages(
        pages_to_create=pages_to_create,
        flow_obj=flow_obj,
        pages_instance=pages_instance,
        flows_map=flows_map,
        flow_name=flow_name,
    )

    event_handler_messages = utils.EventHandlerMessages(
        no_match_1=commons.SCHEDULING_DESIRED_ACTION_NO_MATCH_1,
        no_match_2=commons.SCHEDULING_DESIRED_ACTION_NO_MATCH_2,
        no_input_1=commons.SCHEDULING_DESIRED_ACTION_NO_INPUT_1,
        no_input_2=commons.SCHEDULING_DESIRED_ACTION_NO_INPUT_2,
    )
    event_handlers = utils.create_event_handlers(
        event_handler_messages,
        end_escalation_page=page_map[DesiredActionPageNames.END_ESCALATION],
    )
    flow_obj.event_handlers.extend(event_handlers)

    for route in routes:
        flow_obj.transition_routes.extend([route.transition])

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
        DesiredActionPageNames.END_ESCALATION
    ].proto_obj.transition_routes.extend(
        [
            end_escalation_symbolic_transition,
        ]
    )
    for page_display_name, builder in builder_map.items():
        pages_instance.update_page(
            page_id=page_map[page_display_name], obj=builder.proto_obj
        )

    # update flow
    flows_instance.update_flow(flow_id=flow_obj.name, obj=flow_obj)
