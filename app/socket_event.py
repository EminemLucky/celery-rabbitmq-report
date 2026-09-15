from flask import request
from flask_socketio import emit, join_room, leave_room
from app.extensions import socketio     # ← 只能从这里


@socketio.on("connect")
def handle_connect():
    print(f"[WebSocket] client connected: {request.sid}")
    emit("connected", {"sid": request.sid})


@socketio.on("disconnect")
def handle_disconnect():
    print(f"[WebSocket] client disconnected: {request.sid}")


@socketio.on("subscribe_report")
def handle_subscribe(data):
    report_id = data.get("report_id")
    if report_id:
        room = f"report_{report_id}"
        join_room(room)
        print(f"[WebSocket] {request.sid} subscribed to {room}")


@socketio.on("unsubscribe_report")
def handle_unsubscribe(data):
    report_id = data.get("report_id")
    if report_id:
        room = f"report_{report_id}"
        leave_room(room)
        print(f"[WebSocket] {request.sid} left {room}")