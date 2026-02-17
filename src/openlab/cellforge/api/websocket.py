"""WebSocket handler for real-time simulation streaming."""

from __future__ import annotations

import asyncio
import logging

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


async def simulation_ws(websocket: WebSocket, simulation_id: str) -> None:
    """Stream simulation state updates over WebSocket.

    Sends JSON state snapshots at ~10 Hz while the simulation is running.
    """
    from openlab.cellforge.api.routes.simulation import _simulations

    await websocket.accept()

    if simulation_id not in _simulations:
        await websocket.send_json({"error": "simulation_not_found", "simulation_id": simulation_id})
        await websocket.close()
        return

    entry = _simulations[simulation_id]
    sim = entry["simulation"]
    last_time = -1.0

    try:
        while True:
            state = sim.get_state()
            current_time = state.get("time", 0.0)
            status = entry["status"]

            # Only send if state has changed
            if current_time != last_time:
                snapshot = {
                    "type": "state_update",
                    "simulation_id": simulation_id,
                    "status": status,
                    "time": current_time,
                    "total_time": sim.config.total_time,
                    "progress": current_time / sim.config.total_time if sim.config.total_time > 0 else 0,
                    "state": {
                        "metabolite_concentrations": state.get("metabolite_concentrations", {}),
                        "mrna_counts": {k: v for k, v in state.get("mrna_counts", {}).items()},
                        "protein_counts": {k: v for k, v in state.get("protein_counts", {}).items()},
                        "flux_distribution": state.get("flux_distribution", {}),
                        "growth_rate": state.get("growth_rate", 0.0),
                        "cell_mass": state.get("cell_mass", 0.0),
                        "replication_progress": state.get("replication_progress", 0.0),
                    },
                }
                await websocket.send_json(snapshot)
                last_time = current_time

            # Stop streaming if simulation ended
            if status in ("completed", "stopped", "error"):
                await websocket.send_json({
                    "type": "simulation_ended",
                    "simulation_id": simulation_id,
                    "status": status,
                    "time": current_time,
                })
                break

            await asyncio.sleep(0.1)  # ~10 Hz

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for simulation %s", simulation_id)
    except Exception:
        logger.exception("WebSocket error for simulation %s", simulation_id)
    finally:
        await websocket.close()
