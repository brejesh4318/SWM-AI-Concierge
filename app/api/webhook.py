import os
from app.db.complaints import already_saved, save_complaint
from app.db.session import SessionLocal

from app.state.conversation_manager import load_user, persist_user


from dotenv import load_dotenv
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from app.services import local_bodies, messages

from app.services.chatbot_service import (
    apply_language,
    build_receipt,
    get_completed_complaint,
    language_of,
    local_body_context,
    select_block,
    select_local_body,
    select_local_body_type,
    show_more_local_bodies,
    process_location_message,
    process_photo_message,
    process_text_message,
)

from app.services.whatsapp_service import (
    send_block_menu,
    send_complaint_menu,
    send_language_menu,
    send_local_body_menu,
    send_local_body_type_menu,
    send_photo_question,
    send_text_message,
)

load_dotenv()

router = APIRouter()

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")


@router.get("/webhook")
async def verify_webhook(request: Request):
    """Answer Meta's webhook verification handshake.

    Args:
        request: The incoming GET request carrying the hub.mode,
            hub.verify_token and hub.challenge query parameters.

    Returns:
        A plain-text response echoing the challenge if the mode is
        'subscribe' and the token matches VERIFY_TOKEN. Otherwise a 403
        response with the text 'Verification failed'.
    """

    params = request.query_params

    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:

        return PlainTextResponse(
            challenge or ""
        )

    return PlainTextResponse(
        "Verification failed",
        status_code=403,
    )
def _sender_of(data: dict):
    """Dig the phone number out before the main handler runs.

    Args:
        data: The parsed JSON body of a WhatsApp webhook call.

    Returns:
        The sender's phone number, or None if the payload holds no
        message (for example a delivery receipt or status update).
    """

    try:
        value = data["entry"][0]["changes"][0]["value"]
        return value["messages"][0]["from"]
    except (KeyError, IndexError, TypeError):
        return None


@router.post("/webhook")
async def receive_webhook(request: Request):
    """Receive a WhatsApp webhook call and handle the user's message.

    Loads the sender's saved conversation from the database, processes
    the message, and always saves the conversation again afterwards.

    Args:
        request: The incoming POST request with the webhook JSON body.

    Returns:
        A dictionary with a 'status' key set to 'received'.
    """

    data = await request.json()

    sender = _sender_of(data)

    if sender is None:
        # Delivery receipts and status updates carry no message.
        return {"status": "received"}

    async with SessionLocal() as session:

        await load_user(sender, session)

        try:
            return await _process(data, session)

        finally:
            await persist_user(sender, session)


async def _process(data: dict, session=None):
    """Route one incoming WhatsApp message to the chatbot and reply.

    Handles text, interactive (list and button replies), location and
    image messages. Anything else gets an 'unsupported' reply. The
    chatbot's result is then turned into the matching WhatsApp message
    or menu. Any error is printed and swallowed so WhatsApp does not
    keep retrying the delivery.

    Args:
        data: The parsed JSON body of a WhatsApp webhook call.

    Returns:
        A dictionary with a 'status' key set to 'received'.
    """

    try:


        value = (
            data["entry"][0]
            ["changes"][0]
            ["value"]
        )

        contacts = value.get(
            "contacts",
            [],
        )

        incoming_messages = value.get(
            "messages",
            [],
        )

        if not incoming_messages:
            return {
                "status": "received",
            }

        message = incoming_messages[0]

        sender = message.get("from")

        message_type = message.get(
            "type"
        )

        # ----------------------------------------
        # SAVE USER DETAILS
        # ----------------------------------------

        if contacts:

            profile = contacts[0].get(
                "profile",
                {},
            )

            customer_name = profile.get(
                "name"
            )

            if customer_name:
                from app.state.conversation_manager import save_data

                save_data(
                    sender,
                    "customer_name",
                    customer_name,
                )

        from app.state.conversation_manager import save_data

        save_data(
            sender,
            "phone_number",
            sender,
        )

        # ----------------------------------------
        # TEXT MESSAGE
        # ----------------------------------------

        if message_type == "text":

            message_text = message[
                "text"
            ]["body"]

            result = process_text_message(
                user_id=sender,
                message=message_text,
            )

        # ----------------------------------------
        # INTERACTIVE MESSAGE
        # ----------------------------------------

        elif message_type == "interactive":

            interactive = message.get(
                "interactive",
                {},
            )

            interactive_type = interactive.get(
                "type"
            )

            if interactive_type == "list_reply":

                reply = interactive.get(
                    "list_reply",
                    {},
                )

                reply_id = reply.get(
                    "id"
                )

                if reply_id in local_bodies.TYPE_IDS:

                    result = select_local_body_type(
                        user_id=sender,
                        body_type=local_bodies.TYPE_IDS[
                            reply_id
                        ],
                    )

                elif reply_id in local_bodies.BLOCK_IDS:

                    result = select_block(
                        user_id=sender,
                        block=local_bodies.BLOCK_IDS[
                            reply_id
                        ],
                    )

                elif reply_id == local_bodies.MORE_ID:

                    result = show_more_local_bodies(
                        user_id=sender,
                    )

                elif local_bodies.index_for_row(
                    reply_id
                ) is not None:

                    result = select_local_body(
                        user_id=sender,
                        index=local_bodies.index_for_row(
                            reply_id
                        ),
                    )

                # Convert complaint ID to
                # the corresponding numeric choice
                elif reply_id is not None:

                    complaint_id_to_number = {
                        "complaint_1": "1",
                        "complaint_2": "2",
                        "complaint_3": "3",
                        "complaint_4": "4",
                        "complaint_5": "5",
                        "complaint_6": "6",
                    }

                    selected_option = (
                        complaint_id_to_number.get(
                            reply_id
                        )
                    )

                    if selected_option:

                        result = process_text_message(
                            user_id=sender,
                            message=selected_option,
                        )

                    else:

                        result = {
                            "type": "text",
                            "message": messages.t(
                                language_of(sender),
                                "invalid_option",
                            ),
                        }

            elif interactive_type == "button_reply":

                reply = interactive.get(
                    "button_reply",
                    {},
                )

                reply_id = reply.get(
                    "id"
                )

                if reply_id in messages.LANGUAGE_IDS:

                    result = apply_language(
                        user_id=sender,
                        language=messages.LANGUAGE_IDS[
                            reply_id
                        ],
                    )

                elif reply_id == "photo_yes":

                    result = process_text_message(
                        user_id=sender,
                        message="yes",
                    )

                elif reply_id == "photo_no":

                    result = process_text_message(
                        user_id=sender,
                        message="no",
                    )

                else:

                    result = {
                        "type": "text",
                        "message": messages.t(
                            language_of(sender),
                            "invalid_option",
                        ),
                    }

            else:

                result = {
                    "type": "text",
                    "message": messages.t(
                        language_of(sender),
                        "use_options",
                    ),
                }

        # ----------------------------------------
        # LOCATION MESSAGE
        # ----------------------------------------

        elif message_type == "location":

            location = message.get(
                "location",
                {},
            )

            latitude = location.get(
                "latitude"
            )

            longitude = location.get(
                "longitude"
            )

            if latitude and longitude:

                result = process_location_message(
                    user_id=sender,
                    latitude=latitude,
                    longitude=longitude,
                )

            else:

                result = {
                    "type": "text",
                    "message": messages.t(
                        language_of(sender),
                        "location_unreadable",
                    ),
                }

        # ----------------------------------------
        # IMAGE MESSAGE
        # ----------------------------------------

        elif message_type == "image":

            image = message.get(
                "image",
                {},
            )

            media_id = image.get(
                "id"
            )

            if media_id:

                result = process_photo_message(
                    user_id=sender,
                    media_id=media_id,
                )

            else:

                result = {
                    "type": "text",
                    "message": messages.t(
                        language_of(sender),
                        "photo_unreadable",
                    ),
                }

        # ----------------------------------------
        # UNSUPPORTED MESSAGE
        # ----------------------------------------

        else:

            result = {
                "type": "text",
                "message": messages.t(
                    language_of(sender),
                    "unsupported",
                ),
            }

        # ----------------------------------------
        # SEND RESPONSE
        # ----------------------------------------

        result_type = result["type"]

        language = language_of(sender)

        if result_type == "language_menu":

            await send_language_menu(
                recipient_phone=sender,
            )

        elif result_type == "complaint_menu":

            await send_complaint_menu(
                recipient_phone=sender,
                language=language,
            )

        elif result_type == "local_body_type_menu":

            await send_local_body_type_menu(
                recipient_phone=sender,
                language=language,
            )

        elif result_type == "block_menu":

            await send_block_menu(
                recipient_phone=sender,
                language=language,
                body_type=local_body_context(
                    sender
                )["body_type"],
            )

        elif result_type == "local_body_menu":

            context = local_body_context(sender)

            await send_local_body_menu(
                recipient_phone=sender,
                language=language,
                body_type=context["body_type"],
                block=context["block"],
                offset=context["offset"],
            )

        elif result_type == "photo_question":

            await send_photo_question(
                recipient_phone=sender,
                language=language,
            )

        elif result_type == "text":

            await send_text_message(
                recipient_phone=sender,
                message=result["message"],
            )

        elif result_type == "completed":

            complaint = get_completed_complaint(
                sender
            )

            wamid = message.get("id")

            saved = await already_saved(session, wamid)

            if saved is None:
                saved = await save_complaint(
                    session,
                    complaint,
                    wamid=wamid,
                )

                await session.commit()

            print(
                "\n===== COMPLAINT COMPLETED ====="
            )

            print(
                complaint
            )

            print(
                "================================\n"
            )

            await send_text_message(
                recipient_phone=sender,
                message=build_receipt(
                    language,
                    saved.reference_no,
                    complaint,
                ),
            )

        return {
            "status": "received",
        }

    except Exception as e:

        print(
            "Webhook processing error:",
            repr(e),
        )

        return {
            "status": "received",
        }