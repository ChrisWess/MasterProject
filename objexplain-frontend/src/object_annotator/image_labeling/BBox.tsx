import React from "react";

interface BBoxProps {
    objIdx: number;
    tlx: number;
    tly: number;
    brx: number;
    bry: number;
    opacity: number;
    color: string;
    onContextMenu?: (e: React.MouseEvent<SVGRectElement, MouseEvent>, bbox: number[]) => void;
}

function BoundingBox({objIdx, tlx, tly, brx, bry, opacity, color, onContextMenu}: BBoxProps) {
    let bboxIdx = objIdx % 10;

    return (
        <rect
            className={`bbox-${bboxIdx}`}
            x={tlx}
            y={tly}
            width={brx - tlx}
            height={bry - tly}
            stroke={color}
            opacity={opacity}
            strokeWidth={3}
            fill={"transparent"}
            onContextMenu={(e) => onContextMenu && onContextMenu(e, [tlx, tly, brx, bry])}
        />
    );
}

export default BoundingBox;
