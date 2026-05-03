RS232_BAUDRATE = 19200
RS232_BYTESIZE = 8
RS232_PARITY = "N"
RS232_STOPBITS = 1


def start_command() -> str:
    return "%START#"


def get_param_command() -> str:
    return "%get#"


def _fmt_4(v: float) -> str:
    try:
        n = int(round(float(v) * 100.0))
    except Exception:
        n = 0
    if n < 0:
        n = 0
    if n > 9999:
        n = 9999
    return f"{n:04d}"


def _fmt_4_len(v: float) -> str:
    try:
        n = int(round(float(v) * 10.0))
    except Exception:
        n = 0
    if n < 0:
        n = 0
    if n > 9999:
        n = 9999
    return f"{n:04d}"


def set_param_command(
    width_mm: float,
    thickness_mm: float,
    sample_length_mm: float,
    depth_of_notch: float,
    error_of_mc: float,
    scale_hammer: float,
) -> str:
    return (
        f"%setparam${_fmt_4(width_mm)}${_fmt_4(thickness_mm)}${_fmt_4_len(sample_length_mm)}"
        f"${_fmt_4(depth_of_notch)}${_fmt_4(error_of_mc)}${_fmt_4(scale_hammer)}#"
    )
