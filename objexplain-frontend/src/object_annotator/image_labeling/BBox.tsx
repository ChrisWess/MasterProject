import React from "react";
import {BBOX_COLORS} from "../../document/ProjectIDocPage";

interface BBoxProps {
    objIdx: number;
    // TODO: opaqueness
    tlx: number;
    tly: number;
    brx: number;
    bry: number;
    onContextMenu: (e: React.MouseEvent<SVGRectElement, MouseEvent>, bbox: number[]) => void;
}

function BoundingBox({objIdx, tlx, tly, brx, bry, onContextMenu}: BBoxProps) {
    let bboxIdx = objIdx % 10;
    console.log(BBOX_COLORS[bboxIdx])

    return (
        <rect
            className={`bbox-${bboxIdx}`}
            x={tlx}
            y={tly}
            width={brx - tlx}
            height={bry - tly}
            stroke={BBOX_COLORS[bboxIdx]}
            strokeWidth={3}
            fill={"transparent"}
            onContextMenu={(e) => onContextMenu(e, [tlx, tly, brx, bry])}
        />
    );
}

export default BoundingBox;
