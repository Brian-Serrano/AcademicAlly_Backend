from itertools import groupby

from flask import Blueprint, request, jsonify
from sqlalchemy import or_, and_, not_

from config import db
from db import User, SupportChat
from routes.admin_auth_wrapper import admin_auth_required
from utils import map_search_user_admin, map_chats, support_key

admin_bp = Blueprint("admin_routes", __name__)


@admin_bp.route("/ban_user", methods=["POST"])
@admin_auth_required
def ban_user(current_admin):
    try:
        data = request.get_json()
        user = User.query.filter_by(id=data["userId"]).first()
        user.is_banned = data["value"]
        db.session.commit()
        return jsonify({"data": {"message": "Success"}, "type": "success"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@admin_bp.route("/search_users", methods=["GET"])
@admin_auth_required
def search_users(current_admin):
    try:
        search_query = request.args.get("search_query")
        users = User.query.filter(User.name.ilike(f'%{search_query}%')).all()
        response = [map_search_user_admin(x) for x in users]
        return jsonify({"data": response, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@admin_bp.route("/get_support_messages_from_admin", methods=["GET"])
@admin_auth_required
def get_support_messages_from_admin(current_admin):
    try:
        chats = sorted(SupportChat.query.filter_by(is_closed=False).all(), key=support_key)
        response = [map_chats(k, g) for k, g in groupby(chats, support_key)]
        return jsonify({"data": response, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@admin_bp.route("/get_support_message_with_user", methods=["GET"])
@admin_auth_required
def get_support_message_with_user(current_admin):
    try:
        user_id = request.args.get("user_id")
        chats = SupportChat.query.filter(and_(not_(SupportChat.is_closed), or_(SupportChat.to_id == user_id, SupportChat.from_id == user_id))).all()
        return jsonify({"data": map_chats(user_id, chats), "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@admin_bp.route("/send_support_message", methods=["POST"])
@admin_auth_required
def send_support_message(current_admin):
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


@admin_bp.route("/close_support_chat", methods=["POST"])
@admin_auth_required
def close_support_chat(current_admin):
    try:
        data = request.get_json()
        chats = SupportChat.query.filter(and_(not_(SupportChat.is_closed), or_(SupportChat.to_id == data["userId"], SupportChat.from_id == data["userId"]))).all()

        for chat in chats:
            chat.is_closed = True

        db.session.commit()
        return jsonify({"data": {"message": "Success"}, "type": "success"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500
