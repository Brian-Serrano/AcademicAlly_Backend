from flask import Blueprint, jsonify, request

from config import db
from db import SupportChat
from routes.auth_wrapper import auth_required

support_bp = Blueprint("support_routes", __name__)


@support_bp.route("/get_support_messages", methods=["GET"])
@auth_required
def get_support_messages(current_user):
    try:
        messages = SupportChat.query.filter((SupportChat.from_id == current_user["id"]) | (SupportChat.to_id == current_user["id"])).all()
        response = [{"chatId": x.chat_id, "message": x.message, "fromId": x.from_id, "toId": x.to_id, "date": x.date.strftime("%d/%m/%Y %I:%M %p")} for x in messages]
        return jsonify({"data": response, "currentUser": current_user, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@support_bp.route("/send_support_message", methods=["POST"])
@auth_required
def send_support_message(current_user):
    try:
        data = request.get_json()
        support = SupportChat(
            message=data["message"],
            from_id=data["fromId"],
            to_id=data["toId"]
        )
        db.session.add(support)
        db.session.commit()
        return jsonify({"data": {"message": "Success"}, "type": "success"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500
