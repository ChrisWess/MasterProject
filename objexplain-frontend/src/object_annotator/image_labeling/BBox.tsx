import React from "react";

interface BBoxProps {
    objId: string;
    color: string;
    tlx: number;
    tly: number;
    brx: number;
    bry: number;
    onContextMenu: (e: React.MouseEvent<SVGRectElement, MouseEvent>, bbox: number[]) => void;
}

function BoundingBox({objId, color, tlx, tly, brx, bry, onContextMenu}: BBoxProps) {

    return (
        <rect
            className={`bbox-${objId}`}
            key={objId}
            x={tlx}
            y={tly}
            width={brx - tlx}
            height={bry - tly}
            stroke={color}
            strokeWidth={3}
            fill={"transparent"}
            onContextMenu={(e) => onContextMenu(e, [tlx, tly, brx, bry])}
        />
    );
}

export default BoundingBox;
