from enum import Enum

from dfcx_scrapi.builders.pages import PageBuilder
from dfcx_scrapi.builders.routes import TransitionRouteBuilder  # noqa: E501
from dfcx_scrapi.core.flows import Flows
from dfcx_scrapi.core.intents import Intents
from dfcx_scrapi.core.pages import Pages
from dfcx_scrapi.core.webhooks import Webhooks

import commons
import utils
from resources import wrapup_intents


class WrapUpPageNames(str, Enum):
    END_ESCALATE = "end escalate"
    GET_PROVIDER_NAME = "get provider name"
    SPEAK_PROVIDER_NAME = "speak provider name"


def create_flow_pages(
    config: utils.Config,
    flow_display_name="Wrapup Block",
):
    utils.create_intents(config, wrapup_intents.INTENTS)

    agent_id = utils.get_agent_id(config)
    flows_instance = Flows()
    try:
        flow_obj = flows_instance.get_flow_by_display_name(
            flow_display_name, agent_id
        )
    except ValueError:
        flow_obj = flows_instance.create_flow(
            agent_id=agent_id, display_name=flow_display_name
        )
        pass
    except Exception as e:
        utils.logger.error(e)
        raise

    pages_instance = Pages(creds_path=config.service_account_key)
    pages_to_create = [page.value for page in WrapUpPageNames]

    builder_map = {}
    for page in pages_to_create:
        page_builder = PageBuilder()
        page_builder.create_new_proto_obj(display_name=page, overwrite=True)
        builder_map[page] = page_builder
    for page_display_name, builder in builder_map.items():
        try:
            pages_instance.create_page(
                obj=builder.proto_obj, flow_id=flow_obj.name
            )
        except Exception as e:
            print(e)
            pass

    flows_map = flows_instance.get_flows_map(agent_id, reverse=True)
    page_map = pages_instance.get_pages_map(
        flows_map[flow_display_name], reverse=True
    )

    intents_instance = Intents()
    intents_map = intents_instance.get_intents_map(agent_id, True)

    webhooks_instance = Webhooks(agent_id=agent_id)
    webhook_map = webhooks_instance.get_webhooks_map(
        agent_id=agent_id, reverse=True
    )
    # Start Page
    speak_provider_name_tr = TransitionRouteBuilder().create_new_proto_obj(
        condition="true",
        trigger_fulfillment=utils.create_fulfillment_builder(
            tag="success_path",
            parameter_presets={
                "premature_hang_up": False,
                "wrap_codes": "$sys.func.APPEND($session.params.wrap_codes, "
                '"success")',
            },
        ).proto_obj,
        overwrite=True,
        target_page=page_map[WrapUpPageNames.SPEAK_PROVIDER_NAME],
    )

    flow_obj.transition_routes.clear()
    tr_extends = [speak_provider_name_tr]
    flow_obj.transition_routes.extend(tr_extends)

    # speak provider name page
    spn_page: Pages = builder_map[
        WrapUpPageNames.SPEAK_PROVIDER_NAME
    ].proto_obj
    spn_page.entry_fulfillment = utils.create_fulfillment_builder(
        response_message={
            "message": commons.SPEAK_PROVIDER_NAME,
            "type": "text",
        },
    ).proto_obj
    builder_map[WrapUpPageNames.SPEAK_PROVIDER_NAME].proto_obj = spn_page
    spn_page.transition_routes.clear()
    spn_page.transition_routes.extend(
        [
            TransitionRouteBuilder().create_new_proto_obj(
                intent=intents_map[utils.IntentNames.WRAPUP_WAIT],
                trigger_fulfillment=utils.create_fulfillment_builder(
                    webhook=webhook_map[
                        utils.WebHookNames.UPSERT_DATA_INTO_SPANNER.value
                    ],
                    parameter_presets={
                        "premature_hang_up": True,
                        "wrap_codes": [],
                    },
                    tag="need_extra_with_wait",
                ).proto_obj,
                target_flow=flows_map[utils.FlowNames.ANYTHING_ELSE],
            ),
            TransitionRouteBuilder().create_new_proto_obj(
                intent=intents_map[
                    utils.IntentNames.PREBUILT_COMPONENTS_ESCALATE_HUMAN_AGENT
                ],
                target_page=page_map[WrapUpPageNames.END_ESCALATE],
            ),
        ]
    )
    spn_page.event_handlers.clear()
    spn_page.event_handlers.extend(
        [
            utils.create_event_handler(
                utils.EventNames.NO_INPUT_DEFAULT,
                None,
                page_map[utils.SymbolicPages.END_SESSION],
            ),
        ]
    )

    # end escalate page
    builder_map[
        WrapUpPageNames.END_ESCALATE
    ].proto_obj.transition_routes.extend(
        [
            TransitionRouteBuilder().create_new_proto_obj(
                condition="true",
                overwrite=True,
                target_page=utils.get_symbolic_page(
                    flow_obj.name,
                    utils.SymbolicPages.END_FLOW_WITH_HUMAN_ESCALATION,
                ).name,
            )
        ]
    )

    for page_display_name, builder in builder_map.items():
        print(page_map[page_display_name])
        print("-" * 100, "\n")
        pages_instance.update_page(
            page_id=page_map[page_display_name], obj=builder.proto_obj
        )

    flows_instance.update_flow(flow_id=flow_obj.name, obj=flow_obj)
