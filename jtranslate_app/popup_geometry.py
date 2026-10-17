"""Geometry for the borderless popup, in monitor work-area coordinates."""


def constrain_rect(rect, bounds):
    x,y,w,h = rect
    left,top,right,bottom = bounds
    w = min(max(320,w),right-left)
    h = min(max(100,h),bottom-top)
    return min(max(left,x),right-w), min(max(top,y),bottom-h), w,h


def resize_rect(rect, edge, dx, dy, bounds):
    x,y,w,h = constrain_rect(rect,bounds)
    right,bottom = x+w,y+h
    left_limit,top_limit,right_limit,bottom_limit = bounds
    if 'w' in edge:
        x = max(left_limit,min(x+dx,right-min(320,right_limit-left_limit)))
    if 'e' in edge:
        right = min(right_limit,max(x+min(320,right_limit-left_limit),right+dx))
    if 'n' in edge:
        y = max(top_limit,min(y+dy,bottom-min(100,bottom_limit-top_limit)))
    if 's' in edge:
        bottom = min(bottom_limit,max(y+min(100,bottom_limit-top_limit),bottom+dy))
    return x,y,right-x,bottom-y
