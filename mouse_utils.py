import win32gui
import win32api
import numpy as np
import time


def wind_mouse(
    start_x,
    start_y,
    dest_x,
    dest_y,
    G_0=9,
    W_0=3,
    M_0=15,
    D_0=12,
    move_mouse=lambda x, y: None,
):
    sqrt3 = np.sqrt(3)
    sqrt5 = np.sqrt(5)
    G_0 *= 0.85 + 0.3 * np.random.random()
    W_0 *= 0.8 + 0.4 * np.random.random()
    M_0 *= 0.9 + 0.2 * np.random.random()
    D_0 *= 0.95 + 0.1 * np.random.random()
    current_x, current_y = float(start_x), float(start_y)
    v_x = v_y = W_x = W_y = 0.0
    total_dist = np.hypot(dest_x - start_x, dest_y - start_y)
    if total_dist == 0:
        return
    while (dist := np.hypot(dest_x - current_x, dest_y - current_y)) >= 1:
        progress = 1 - (dist / total_dist)
        W_mag = min(W_0 * (1 + progress * 0.5), dist) * (0.9 + 0.2 * np.random.random())
        G_adaptive = G_0 * (1 + progress * 2) * min(1, dist / 10)
        if dist >= D_0:
            rand_x = (2 * np.random.random() - 1) * (1 + np.random.random() * 0.2)
            rand_y = (2 * np.random.random() - 1) * (1 + np.random.random() * 0.2)
            W_x = W_x / sqrt3 + rand_x * W_mag / sqrt5
            W_y = W_y / sqrt3 + rand_y * W_mag / sqrt5
        else:
            W_x /= sqrt3 * (1 + progress)
            W_y /= sqrt3 * (1 + progress)
            if M_0 < 3:
                M_0 = np.random.random() * 2 + 3
            else:
                M_0 /= sqrt5 * (1 + progress * 0.5)
        v_x += W_x + G_adaptive * (dest_x - current_x) / dist
        v_y += W_y + G_adaptive * (dest_y - current_y) / dist
        v_mag = np.hypot(v_x, v_y)
        if v_mag > M_0:
            v_clip = M_0 * (0.7 + 0.3 * np.random.random())
            v_x = (v_x / v_mag) * v_clip
            v_y = (v_y / v_mag) * v_clip
        jitter_x = (np.random.random() - 0.5) * 0.15
        jitter_y = (np.random.random() - 0.5) * 0.15
        current_x += v_x + jitter_x
        current_y += v_y + jitter_y
        new_dist = np.hypot(dest_x - current_x, dest_y - current_y)
        if new_dist > dist and dist < 5:
            v_x *= 0.5
            v_y *= 0.5
            current_x = current_x - v_x * 0.5
            current_y = current_y - v_y * 0.5
        move_x = int(np.round(current_x))
        move_y = int(np.round(current_y))
        if abs(move_x - start_x) >= 1 or abs(move_y - start_y) >= 1:
            move_mouse(move_x, move_y)
            start_x, start_y = move_x, move_y
        if v_mag < 0.1 and dist < 2:
            break
    final_x, final_y = int(np.round(dest_x)), int(np.round(dest_y))
    if abs(final_x - start_x) >= 1 or abs(final_y - start_y) >= 1:
        move_mouse(final_x, final_y)


def move_mouse_in_window(hwnd, dest_x, dest_y, verbose=True, **kwargs):
    if not win32gui.IsWindow(hwnd):
        raise ValueError(f"Invalid window handle: {hwnd}")

    try:
        client_left, client_top, _, _ = win32gui.GetClientRect(hwnd)
        screen_left, screen_top = win32gui.ClientToScreen(
            hwnd, (client_left, client_top)
        )
    except Exception as e:
        if verbose:
            print(f"Error getting window coordinates: {e}")
        return

    cursor_screen_x, cursor_screen_y = win32api.GetCursorPos()
    start_x = cursor_screen_x - screen_left
    start_y = cursor_screen_y - screen_top

    def win32_move_mouse(x, y):
        target_screen_x = screen_left + x
        target_screen_y = screen_top + y
        win32api.SetCursorPos((target_screen_x, target_screen_y))
        time.sleep(np.random.uniform(0.002, 0.005))

    if verbose:
        print(
            f"Moving mouse in window from ({start_x}, {start_y}) to ({dest_x}, {dest_y})"
        )

    wind_mouse(
        start_x=start_x,
        start_y=start_y,
        dest_x=dest_x,
        dest_y=dest_y,
        move_mouse=win32_move_mouse,
        **kwargs,
    )

    if verbose:
        print("Mouse movement complete.")
