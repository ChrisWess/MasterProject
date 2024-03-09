import * as d3 from "d3";
import {FC, useCallback, useEffect, useMemo, useRef, useState} from "react";
import {useDispatch, useSelector} from "react-redux";
import BoundingBox from "./BBox";
import BBoxText from "./BBoxText";
import {DetectedObject} from "../../api/models/object";
import {getMappedLabel} from "../ObjectControl";
import {setZoomResetter} from "../../reducers/objectCreateSlice";
import {ImageDocument} from "../../api/models/imgdoc";

interface ImageAnnotatorProps {
    idoc: ImageDocument;
    height: number;
}

const ImageAnnotator: FC<ImageAnnotatorProps> = ({idoc, height}) => {
    const svgRef = useRef<SVGSVGElement>(null);
    const gZoomRef = useRef<SVGGElement>(null);
    const gDragRef = useRef<SVGGElement>(null);
    const rectRef = useRef<SVGRectElement>(null);
    const imgRef = useRef<SVGImageElement>(null);

    // global state (redux)
    const dispatch = useDispatch();
    const labelsMap = useSelector((state: any) => state.iDoc.labelMap);
    const imgUrl: string | undefined = useSelector((state: any) => state.iDoc.imgUrl);
    const isZooming: boolean = useSelector((state: any) => state.newObj.isZooming);

    const [selectedBbox, setSelectedBbox] = useState<DetectedObject | null>(null);

    const handleRightClick = useCallback((event: any, obj: DetectedObject) => {
            event.preventDefault();
            const rect = event.target.getBoundingClientRect();
            const position = {
                left: rect.left,
                top: rect.top + rect.height,
            };
            // TODO: take position
            setSelectedBbox(obj);
        }, [],
    );

    // drag handling
    const drag = useMemo(() => d3.drag<SVGGElement, unknown>(), []);

    const handleDragStart = (event: d3.D3DragEvent<any, any, any>, _: any) => {
        if (!rectRef.current) return;

        const myRect = d3.select(rectRef.current);
        myRect
            .attr("xOrigin", event.x)
            .attr("yOrigin", event.y)
            .attr("x", event.x)
            .attr("width", 0)
            .attr("y", event.y)
            .attr("height", 0);
    };

    const handleDrag = (event: d3.D3DragEvent<any, any, any>, _: any) => {
        if (!rectRef.current) return;

        const myRect = d3.select(rectRef.current);
        const myImage = d3.select(imgRef.current).node()!.getBBox();

        const x = parseInt(myRect.attr("xOrigin"));
        const y = parseInt(myRect.attr("yOrigin"));
        const w = Math.abs(event.x - x);
        const h = Math.abs(event.y - y);

        if (event.x < x && event.y < y) {
            myRect
                .attr("y", Math.max(0, y - h))
                .attr("x", Math.max(0, x - w))
                .attr("width", Math.min(w, x))
                .attr("height", Math.min(h, y));
        } else if (event.x < x) {
            const maxHeight = myImage.height - y;
            myRect
                .attr("x", Math.max(0, x - w))
                .attr("width", Math.min(w, x))
                .attr("height", Math.min(h, maxHeight));
        } else if (event.y < y) {
            const maxWidth = myImage.width - x;
            myRect
                .attr("width", Math.min(w, maxWidth))
                .attr("y", Math.max(0, y - h))
                .attr("height", Math.min(h, y));
        } else {
            const maxWidth = myImage.width - x;
            const maxHeight = myImage.height - y;
            myRect.attr("width", Math.min(w, maxWidth)).attr("height", Math.min(h, maxHeight));
        }
    };

    const handleDragEnd = (_event: d3.D3DragEvent<any, any, any>, _: any) => {
        const myRect = d3.select(rectRef.current);
        const width = parseInt(myRect.attr("width"));
        const height = parseInt(myRect.attr("height"));

        // only open the code selector if the rect is big enough
        if (width > 10 && height > 10) {
            const boundingBox = myRect.node()!.getBoundingClientRect();
            const position = {
                left: boundingBox.left,
                top: boundingBox.top + boundingBox.height,
            };
            // TODO: get bounding box position and dimensions and save in state.
            //   On Button Click in NewObjectControl Panel (after label & categories are defined),
            //   fire an object insert into IDoc with collected data. Make Bounding Box half transparent
            //   after the operation (like the other BBoxs), which is fixed in and read from idoc now.
            //   When dragging, we draw the next BBox.
        } else {
            resetRect();
        }
    };

    const resetRect = () => {
        const myRect = d3.select(rectRef.current);
        myRect.attr("width", 0).attr("height", 0);
    };

    // main zoom element
    const zoom = useMemo(() =>
        d3.zoom<SVGSVGElement, unknown>().scaleExtent([0.5, 5]), []);

    const handleZoom = useCallback((e: d3.D3ZoomEvent<any, any>) => {
        d3.select(gZoomRef.current).attr("transform", e.transform.toString());
    }, []);

    const setupZoom = () => {
        const svg = d3.select<SVGSVGElement, unknown>(svgRef.current!);
        const gDrag = d3.select<SVGGElement, unknown>(gDragRef.current!);

        if (!isZooming) {
            svg.on(".zoom", null);

            drag.on("start", handleDragStart);
            drag.on("drag", handleDrag);
            drag.on("end", handleDragEnd);
            gDrag.call(drag);
        } else {
            gDrag.on(".drag", null);

            zoom.on("zoom", handleZoom);
            svg.call(zoom);
        }
    };

    useEffect(() => {
        if (svgRef.current) {
            setupZoom();
        }
    }, [zoom, svgRef, handleZoom, isZooming]);

    const resetZoom = useCallback(() => {
        const svg = d3.select<SVGSVGElement, unknown>(svgRef.current!);
        svg.transition().duration(750).call(zoom.transform, d3.zoomIdentity);
    }, [zoom, svgRef])

    useEffect(() => {
        dispatch(setZoomResetter(resetZoom));
    }, []);

    return (
        <svg
            ref={svgRef}
            width="100%"
            height={Math.max(500, height) + "px"}
            style={{cursor: isZooming ? "move" : "auto"}}
        >
            <g ref={gZoomRef}>
                <g ref={gDragRef} style={{cursor: isZooming ? "move" : "crosshair"}}>
                    <image ref={imgRef} href={imgUrl} style={{outline: "1px solid black"}}/>
                    <rect
                        ref={rectRef}
                        x={0}
                        y={0}
                        stroke={"black"}
                        strokeWidth={3}
                        fill={"transparent"}
                        width={0}
                        height={0}
                    ></rect>
                </g>
                <g>
                    {idoc.objects?.map((obj: DetectedObject, index: number) => (
                        <BoundingBox key={'bboxRect' + index} objIdx={index}
                                     tlx={obj.tlx} tly={obj.tly} brx={obj.brx} bry={obj.bry}
                                     onContextMenu={(e) => handleRightClick(e, obj)}/>
                    ))}
                </g>
                <g>
                    {idoc.objects?.map((obj: DetectedObject, index: number) => (
                        <BBoxText
                            key={'bboxText' + index}
                            text={getMappedLabel(labelsMap, obj.labelId)!.name}
                            tlx={obj.tlx} tly={obj.tly} brx={obj.brx} bry={obj.bry}
                            onContextMenu={(e) => handleRightClick(e, obj)}
                            fontSize={Math.max(21, height / 17)}
                        />
                    ))}
                </g>
            </g>
        </svg>
    );
}

export default ImageAnnotator;