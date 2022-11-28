from ..app import skt
from flask_socketio import emit, send
from flask_socketio import join_room, leave_room
from typing import List
from ..models.room import Room
from ..models.player import Player
from uuid import uuid1
from flask import request, session
import json


def get_room_code(code: str) -> Room:
    " Gets a room with the code provided "
    for room in rooms:
        if room.room_code == code:
            return room
    # throw the exception to stop execution
    raise Exception(f"Unable to find room with code {code}")
    return None


def get_room_uuid(uuid: str) -> Room:
    " Gets a room with the room_uuid provided "
    for room in rooms:
        if room.uuid == uuid:
            return room
    # throw the exception to stop execution
    raise Exception(f"Unable to find room with value {uuid} - often occurs when server restarts and clients attempt to maintain connectivity to closed server")
    return None


def get_room_host_uuid(host_uuid:str) -> Room:
    " Gets a room with the host_uuid provided "
    for room in rooms:
        if room.admin_uuid == host_uuid:
            return room
    # throw the exception to stop execution
    raise Exception(f"Unable to find room with host_uuid {host_uuid}")
    return None


def player_list_update(room: Room) -> None:
    data = {"players": [vars(player) for player in room.players]}
    emit("player_list_update", data, to=room.admin_sid)


@skt.on("connect")
def connect(data):
    emit("connect_res", {"Status": "Connected"}, broadcast=False)


@skt.on("check_room")
def check_room(data):
    if get_room_code(data["code"]) != None:
        output = {"room_uuid": get_room_code(data["code"]).uuid}
    else:
        output = {"error": "No room with the provided code exists"}

    emit("check_room_res", output, broadcast=False)


@skt.on("join_room")
def join_comp(data):
    selected_room = get_room_code(data["code"])
    if selected_room is None:
        emit(
            "join_room_res",
            {"error": "No room with the provided code exists"},
            broadcast=False,
        )

    # associate request SID with a socket "room"
    join_room(selected_room.uuid)

    player = Player(data["name"], data["skill"], request.sid)
    # associate player information with chessScheduel game
    selected_room.add_player(player)
    emit("join_room_res", {"user_uuid": player.uuid}, broadcast=False)
    player_list_update(selected_room)


@skt.on("get_all_players")
def get_all_players(data):
    player_list_update(get_room_uuid(data["room_uuid"]))


# maintain a list of active rooms
rooms: List[Room] = list()


@skt.on("create_room")
def create(data):
    admin_uuid = str(uuid1())
    admin_sid = request.sid
    room = Room(admin_uuid, admin_sid, session)
    rooms.append(room)
    emit(
        "create_room_res",
        {"host_uuid": admin_uuid, "room_uuid": room.uuid, "room_code": room.room_code},
        broadcast=False,
    )
    # debug
    for i in range(5):
        a = Player(str(i), 5, 5000)
        a.rating += i*100
        room.add_player(a)
    player_list_update(room)


@skt.on("delete_room")
def delete_room(data):
    selected_room = get_room_uuid(data["room_uuid"]) or None

    if not selected_room:
        emit(
            "delete_room_res",
            {"error": "No room with provided UUID exists"},
            broadcast=False,
        )
        return

    if data["user_uuid"] == room.admin_uuid:
        # tell all clients to leave the room
        emit("delete_room_res", {"message": "Room closed by admin"}, to=room.uuid)


@skt.on("check_name")
def check_name(data):
    " Valid if name is not taken, and not valid if name is taken. "
    emit(
        "check_name_res",
        {"valid": not get_room_uuid(data["room_uuid"]).name_is_taken(data["name"])},
        broadcast=False,
    )


@skt.on("start_game")
def start_game(data):
    room = get_room_host_uuid(data["host_uuid"])
    if room is None:
        emit("start_game_res", {"status" : 500}, broadcast=False)
    else:
        emit("start_game_res", {"status" :200}, broadcast=False)
    
    emit("pairings", {"round":room.rounds, "pairings":room.get_pairings()}, to=room.uuid)