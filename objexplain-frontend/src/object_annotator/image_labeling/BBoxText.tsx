import React from "react";

interface BBoxTextProps {
    text: string;
    tlx: number;
    tly: number;
    brx: number;
    bry: number;
    onContextMenu?: (e: React.MouseEvent<SVGTextElement, MouseEvent>, bbox: number[]) => void;
    fontSize: number;
}

function BBoxText({text, tlx, tly, brx, bry, onContextMenu, fontSize}: BBoxTextProps) {

    return (
        <text
            key={text}
            x={tlx + 3}
            y={tly + fontSize}
            width={brx - tlx}
            height={bry - tly}
            fill={"white"}
            stroke={"gray"}
            strokeWidth={0.75}
            fontSize={`${fontSize}px`}
            onContextMenu={(e) => onContextMenu && onContextMenu(e, [tlx, tly, brx, bry])}
        >
            {text}
        </text>
    );
}

export default BBoxText;
