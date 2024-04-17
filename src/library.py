import os
from enum import Enum
from typing import Iterable, List, Optional, Union

from google.api_core.exceptions import AlreadyExists
from google.cloud import dialogflowcx_v3
from google.cloud.dialogflowcx_v3 import EntityType, Form
from google.cloud.dialogflowcx_v3.types import (
    EventHandler,
    Flow,
    Fulfillment,
    Intent,
    Page,
    ResponseMessage,
    TransitionRoute,
    Webhook,
)

import utils
from resources.utils import Resources

# Get project_id, location, agent_id from environment variables
project_id = os.environ.get("PROJECT_ID")
location = os.environ.get("LOCATION")
config = utils.Config()
agent_name = Resources(config).agent_path
agent_path = dialogflowcx_v3.AgentsClient().parse_agent_path(agent_name)
agent_id = agent_path["agent"]


class StandardPage(Enum):
    START = "START"
    END_FLOW = "END_FLOW"
    END_FLOW_WITH_FAILURE = "END_FLOW_WITH_FAILURE"
    END_FLOW_WITH_HUMAN_ESCALATION = "END_FLOW_WITH_HUMAN_ESCALATION"


class SystemEntityType(Enum):
    ANY = "any"
    DATE = "date"
    DATE_PERIOD = "date-period"
    DATE_TIME = "date-time"
    DURATION = "duration"
    LAST_NAME = "last-name"
    NUMBER = "number"
    PERSON = "person"
    TIME = "time"


class DialogflowLibrary:
    @classmethod
    def get_parent(cls):
        client = dialogflowcx_v3.AgentsClient()
        return client.agent_path(project_id, location, agent_id)

    @classmethod
    def create_flow(cls, flow_name: str):
        client = dialogflowcx_v3.FlowsClient()

        # Initialize request argument(s)
        flow = dialogflowcx_v3.Flow()
        flow.display_name = flow_name
        parent = cls.get_parent()
        try:
            request = dialogflowcx_v3.CreateFlowRequest(
                parent=parent,
                flow=flow,
            )
            response = client.create_flow(request=request)
            return response
        except AlreadyExists:
            flow = cls.get_flow(flow_name)
            request = dialogflowcx_v3.UpdateFlowRequest(flow=flow)
            response = client.update_flow(request=request)
            return response

    @classmethod
    def create_page(
        cls,
        flow: Flow,
        page_name: str,
        entry_fulfillment: Optional[Fulfillment] = None,
        event_handlers: Optional[List[EventHandler]] = None,
        form: Optional[Form] = None,
    ):
        client = dialogflowcx_v3.PagesClient()
        # Initialize request argument(s)
        page = dialogflowcx_v3.Page()
        page.display_name = page_name
        page.entry_fulfillment = entry_fulfillment
        page.event_handlers = event_handlers
        page.form = form
        parent = flow.name

        try:
            request = dialogflowcx_v3.CreatePageRequest(
                parent=parent,
                page=page,
            )
            response = client.create_page(request=request)
            # Handle the response
            return response

        except AlreadyExists:
            page = cls.get_page(flow, page_name)
            page.display_name = page_name
            page.entry_fulfillment = entry_fulfillment
            page.event_handlers = event_handlers

            request = dialogflowcx_v3.UpdatePageRequest(
                page=page,
            )
            response = client.update_page(request=request)
            return response

    @classmethod
    def update_flow(
        cls,
        flow: Flow,
        *,
        event_handlers: List[EventHandler] | None = None,
    ):
        client = dialogflowcx_v3.FlowsClient()

        if event_handlers is not None:
            for event_handler in event_handlers:
                if not utils.is_existing_event_handler(
                    event_handler, flow.event_handlers
                ):
                    flow.event_handlers.extend([event_handler])

        request = dialogflowcx_v3.UpdateFlowRequest(
            flow=flow,
        )
        response = client.update_flow(request=request)
        return response

    @classmethod
    def get_intent(cls, intent_display_name: str):
        client = dialogflowcx_v3.IntentsClient()
        parent = cls.get_parent()
        # Initialize request argument(s)
        request = dialogflowcx_v3.ListIntentsRequest(
            parent=parent,
        )
        # Make the request
        all_intents = client.list_intents(request=request)

        display_name2intent_name = {
            intent.display_name: intent.name for intent in all_intents
        }
        if intent_display_name not in display_name2intent_name:
            raise ValueError(
                f"Intent {intent_display_name} not found in agent {agent_id}"
            )
        intent_name = display_name2intent_name[intent_display_name]

        # Make the request

        intent = client.get_intent(name=intent_name)
        return intent

    @classmethod
    def get_flow(cls, display_name: str) -> Flow | None:
        client = dialogflowcx_v3.FlowsClient()
        parent = cls.get_parent()
        # Initialize request argument(s)
        request = dialogflowcx_v3.ListFlowsRequest(
            parent=parent,
        )
        # Make the request
        all_flows = client.list_flows(request=request)
        display_name2flow_name = {
            flow.display_name: flow.name for flow in all_flows
        }
        flow_name = display_name2flow_name.get(display_name)
        if flow_name is None:
            return None

        flow = client.get_flow(name=flow_name)
        return flow

    @classmethod
    def get_webhook(cls, display_name: str) -> Webhook:
        client = dialogflowcx_v3.WebhooksClient()
        parent = cls.get_parent()
        # Initialize request argument(s)
        request = dialogflowcx_v3.ListWebhooksRequest(
            parent=parent,
        )
        # Make the request
        all_webhooks = client.list_webhooks(request=request)
        display_name2webhook_name = {
            webhook.display_name: webhook.name for webhook in all_webhooks
        }
        webhook_name = display_name2webhook_name[display_name]

        webhook = client.get_webhook(name=webhook_name)
        return webhook

    @classmethod
    def get_entity_type(cls, display_name: str) -> EntityType:
        client = dialogflowcx_v3.EntityTypesClient()
        parent = DialogflowLibrary.get_parent()

        # Initialize request argument(s)
        request = dialogflowcx_v3.ListEntityTypesRequest(
            parent=parent,
        )

        # Make the request
        all_entity_types = client.list_entity_types(request=request)
        display_name2entity_type_name = {
            entity_type.display_name: entity_type.name
            for entity_type in all_entity_types
        }
        entity_type_name = display_name2entity_type_name[display_name]

        entity_type = client.get_entity_type(name=entity_type_name)
        return entity_type

    @classmethod
    def get_system_entity_type(
        cls, entity_type: SystemEntityType
    ) -> EntityType:
        # return cls.get_entity_type(f"sys.{entity_type.value}")

        entity_type_name = f"projects/-/locations/-/agents/-/entityTypes/sys.{entity_type.value}"  # noqa: E501
        return EntityType(name=entity_type_name)

    @classmethod
    def get_page(cls, flow: Flow, display_name: str) -> Page:
        client = dialogflowcx_v3.PagesClient()
        # Initialize request argument(s)
        request = dialogflowcx_v3.ListPagesRequest(
            parent=flow.name,
        )
        # Make the request
        all_pages = client.list_pages(request=request)
        display_name2page_name = {
            page.display_name: page.name for page in all_pages
        }

        page_name = display_name2page_name[display_name]
        page = client.get_page(name=page_name)
        return page

    @classmethod
    def get_standard_page(cls, flow: Flow, page: StandardPage):
        page_name = f"{flow.name}/pages/{page.value}"
        return Page(name=page_name)

    @classmethod
    def create_transition_route(
        cls,
        condition: str = None,
        target_page: Page = None,
        target_flow: Flow = None,
        intent: Intent = None,
        trigger_fulfillment: Fulfillment = None,
    ) -> Optional[TransitionRoute]:
        # only target_page or target_flow can be used
        if target_page and target_flow:
            raise ValueError("Only target_page or target_flow can be used")

        kwargs = {}
        if condition:
            kwargs["condition"] = condition
        if target_page:
            kwargs["target_page"] = target_page.name
        if target_flow:
            kwargs["target_flow"] = target_flow.name
        if intent:
            kwargs["intent"] = intent.name
        if trigger_fulfillment:
            kwargs["trigger_fulfillment"] = trigger_fulfillment
        return TransitionRoute(**kwargs)

    @classmethod
    def create_response_message(cls, text: str) -> ResponseMessage:
        return ResponseMessage(text=ResponseMessage.Text(text=[text]))

    @classmethod
    def create_set_parameter_action(
        cls, parameter: str, value: str | float | int | None
    ) -> Fulfillment.SetParameterAction:
        return Fulfillment.SetParameterAction(parameter=parameter, value=value)

    @classmethod
    def create_fulfillment(
        cls,
        messages: Optional[List[ResponseMessage]] = None,
        webhook: Optional[Webhook] = None,
        tag: Optional[str] = None,
        set_parameter_actions: Optional[
            Iterable[Fulfillment.SetParameterAction]
        ] = None,
    ) -> Fulfillment:
        fullfilment = Fulfillment()
        fullfilment.messages = messages
        if webhook is not None:
            fullfilment.webhook = webhook.name

        fullfilment.tag = tag
        fullfilment.set_parameter_actions = set_parameter_actions
        return fullfilment

    @classmethod
    def create_page_form(cls, parameters: list[Form.Parameter]) -> Form:
        form = Form()
        form.parameters = parameters
        return form

    @classmethod
    def create_page_form_parameter(
        cls,
        *,
        name: str,
        entity_type: EntityType,
        required: bool = True,
        is_list: bool = False,
        redact: bool = False,
        initial_prompt_fulfillment: Optional[Fulfillment] = None,
        reprompt_event_handlers: Optional[List[EventHandler]] = None,
    ) -> Form.Parameter:
        parameter = Form.Parameter()
        parameter.display_name = name
        parameter.required = required
        parameter.entity_type = entity_type.name
        parameter.is_list = is_list
        parameter.redact = redact
        parameter.fill_behavior = Form.Parameter.FillBehavior()
        parameter.fill_behavior.initial_prompt_fulfillment = (
            initial_prompt_fulfillment
        )
        parameter.fill_behavior.reprompt_event_handlers = (
            reprompt_event_handlers
        )
        return parameter

    @classmethod
    def create_event_handler(
        cls,
        name: Optional[str] = None,
        event: str = "sys.no-input-1",
        trigger_fulfillment: Optional[Fulfillment] = None,
        target_page: Optional[Page] = None,
        target_flow: Optional[Flow] = None,
    ) -> EventHandler:
        kwargs = {}
        if name is not None:
            kwargs["name"] = name
        if event is not None:
            kwargs["event"] = event
        if trigger_fulfillment is not None:
            kwargs["trigger_fulfillment"] = trigger_fulfillment
        if target_page is not None:
            kwargs["target_page"] = target_page.name
        if target_flow is not None:
            kwargs["target_flow"] = target_flow.name
        return EventHandler(**kwargs)

    @classmethod
    def add_transition_route(
        cls, parent: Union[Flow, Page], transition: TransitionRoute
    ) -> Optional[Union[Flow, Page]]:
        # add new transition route to the parent
        if isinstance(parent, Flow):
            client = dialogflowcx_v3.FlowsClient()
            current_flow = client.get_flow(name=parent.name)
            current_flow.transition_routes.append(transition)
            request = dialogflowcx_v3.UpdateFlowRequest(
                flow=current_flow,
                update_mask={"paths": ["transition_routes"]},
            )
            response = client.update_flow(request=request)
            return response

        elif isinstance(parent, Page):
            client = dialogflowcx_v3.PagesClient()
            current_page = client.get_page(name=parent.name)
            current_page.transition_routes.append(transition)
            request = dialogflowcx_v3.UpdatePageRequest(
                page=current_page,
                update_mask={"paths": ["transition_routes"]},
            )
            response = client.update_page(request=request)
            return response

        else:
            raise ValueError("parent must be Flow or Page")

    @classmethod
    def get_symbolic(cls, flow: Flow, mode: str):
        symbolic_dict = {
            "failure": Page(name=f"{flow.name}/pages/END_FLOW_WITH_FAILURE"),
            "success": Page(name=f"{flow.name}/pages/END_FLOW"),
            "escalation": Page(
                name=f"{flow.name}/pages/END_FLOW_WITH_HUMAN_ESCALATION"
            ),
        }
        return symbolic_dict[mode]
