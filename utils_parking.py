import numpy as np

def point_in_polygon(point, polygon):
    """
    Ray casting algorithm - checks if a point is inside a polygon.
    """
    x, y = point
    n = len(polygon)
    inside = False
    px, py = polygon[0]

    for i in range(1, n + 1):
        qx, qy = polygon[i % n]
        if min(py, qy) < y <= max(py, qy):
            if x <= max(px, qx):
                if py != qy:
                    x_intersect = (y - py) * (qx - px) / (qy - py) + px
                if px == qx or x <= x_intersect:
                    inside = not inside
        px, py = qx, qy

    return inside


def calculate_iou(bbox, polygon):
    """
    Improved IoU - centroid check + bounding box overlap fallback.
    Works well for elevated/diagonal parking lot images.
    """
    x1, y1, x2, y2 = bbox

    poly_arr = np.array(polygon)
    px1 = float(poly_arr[:, 0].min())
    py1 = float(poly_arr[:, 1].min())
    px2 = float(poly_arr[:, 0].max())
    py2 = float(poly_arr[:, 1].max())

    # --- Check 1: centroid inside polygon ---
    centroid = ((x1 + x2) / 2, (y1 + y2) / 2)
    if point_in_polygon(centroid, polygon):
        inter_x1   = max(x1, px1)
        inter_y1   = max(y1, py1)
        inter_x2   = min(x2, px2)
        inter_y2   = min(y2, py2)
        inter_area = max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1)
        car_area   = (x2 - x1) * (y2 - y1)
        spot_area  = (px2 - px1) * (py2 - py1)
        union_area = car_area + spot_area - inter_area
        return inter_area / union_area if union_area > 0 else 0.0

    # --- Check 2: bounding box overlap fallback ---
    inter_x1 = max(x1, px1)
    inter_y1 = max(y1, py1)
    inter_x2 = min(x2, px2)
    inter_y2 = min(y2, py2)

    if inter_x2 > inter_x1 and inter_y2 > inter_y1:
        inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
        car_area   = (x2 - x1) * (y2 - y1)
        spot_area  = (px2 - px1) * (py2 - py1)
        union_area = car_area + spot_area - inter_area
        return inter_area / union_area if union_area > 0 else 0.0

    return 0.0