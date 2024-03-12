import * as d3 from "d3";
import {ZoomBehavior} from "d3";
import {FC, RefObject, useCallback, useEffect, useMemo, useRef, useState} from "react";
import {useDispatch, useSelector} from "react-redux";
import BoundingBox from "./BBox";
import BBoxText from "./BBoxText";
import {DetectedObject} from "../../api/models/object";
import {ImageDocument} from "../../api/models/imgdoc";
import {setBbox} from "../../reducers/objectCreateSlice";

interface ImageAnnotatorProps {
    svgRef: RefObject<SVGSVGElement>;
    zoom: ZoomBehavior<SVGSVGElement, unknown>;
    height: number;
}

const ImageAnnotator: FC<ImageAnnotatorProps> = ({svgRef, zoom, height}) => {
    const gZoomRef = useRef<SVGGElement>(null);
    const gDragRef = useRef<SVGGElement>(null);
    const rectRef = useRef<SVGRectElement>(null);
    const imgRef = useRef<SVGImageElement>(null);

    // global state (redux)
    const dispatch = useDispatch();
    const labelsMap = useSelector((state: any) => state.iDoc.labelMap);
    const idoc: ImageDocument | undefined = useSelector((state: any) => state.iDoc.document);
    const imgUrl: string | undefined = useSelector((state: any) => state.iDoc.imgUrl);
    const showObjs: boolean = useSelector((state: any) => state.newObj.showCurrObjs);
    const isMoveImg: boolean = useSelector((state: any) => state.newObj.isMoveImg);

    const [selectedBbox, setSelectedBbox] = useState<DetectedObject | null>(null);

    const handleRightClick = useCallback((event: any, obj: DetectedObject) => {
            event.preventDefault();
            const rect = event.target.getBoundingClientRect();
            const bbox_repr = {
                tlx: rect.left, tly: rect.top,
                brx: rect.left + rect.width,
                bry: rect.top + rect.height,
            };
            // TODO: dispatch
            setSelectedBbox(obj);
        }, [],
    );

    let pixelHeight = Math.max(500, height)
    let imgHeight = Math.max(500, height - (height / 10))
    let borderDistHeight = (pixelHeight - imgHeight) / 2
    let imgRatio = idoc ? idoc.width / idoc.height : 0
    let pixelWidth = pixelHeight * imgRatio
    let borderDistWidth: number = imgRatio * borderDistHeight
    let widthRatio = idoc ? idoc.width / (pixelWidth - 2 * borderDistWidth) : 0
    let heightRatio = idoc ? idoc.height / (pixelHeight - 2 * borderDistHeight) : 0

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

        const curr_x = Math.max(event.x, borderDistWidth);
        const curr_y = Math.max(event.y, borderDistHeight);
        const orig_x = parseInt(myRect.attr("xOrigin"));
        const orig_y = parseInt(myRect.attr("yOrigin"));
        const w = Math.abs(curr_x - orig_x);
        const h = Math.abs(curr_y - orig_y);

        if (curr_x < orig_x && curr_y < orig_y) {
            myRect
                .attr("y", orig_y - h)
                .attr("x", orig_x - w)
                .attr("width", w)
                .attr("height", h);
        } else if (curr_x < orig_x) {
            const maxHeight = myImage.height - orig_y + borderDistHeight;
            myRect
                .attr("x", orig_x - w)
                .attr("width", w)
                .attr("height", Math.min(h, maxHeight));
        } else if (curr_y < orig_y) {
            const maxWidth = myImage.width - orig_x + borderDistWidth;
            myRect
                .attr("width", Math.min(w, maxWidth))
                .attr("y", orig_y - h)
                .attr("height", h);
        } else {
            const maxWidth = myImage.width - orig_x + borderDistWidth;
            const maxHeight = myImage.height - orig_y + borderDistHeight;
            myRect.attr("width", Math.min(w, maxWidth)).attr("height", Math.min(h, maxHeight));
        }
    };

    const handleDragEnd = (_event: d3.D3DragEvent<any, any, any>, _: any) => {
        const myRect = d3.select(rectRef.current);
        const width = parseInt(myRect.attr("width"));
        const height = parseInt(myRect.attr("height"));

        // only keep the bbox if it is big enough
        if (idoc && width > 10 && height > 10) {
            // pixelWidth = 2 * borderDistWidth
            const left = parseInt(myRect.attr("x")) - borderDistWidth;
            const top = parseInt(myRect.attr("y")) - borderDistHeight;
            // map screen coordinates to the original image pixels
            let mappedLeft = Math.floor(Math.max(0, left * widthRatio));
            let mappedTop = Math.floor(Math.max(0, top * heightRatio));
            let mappedRight = Math.ceil(Math.min(idoc.width, mappedLeft + (width * widthRatio)));
            let mappedBottom = Math.ceil(Math.min(idoc.height, mappedTop + (height * heightRatio)));
            const bbox_repr = {
                tlx: mappedLeft, tly: mappedTop,
                brx: mappedRight, bry: mappedBottom,
            };
            dispatch(setBbox(bbox_repr))
        } else {
            resetRect();
        }
    };

    const resetRect = () => {
        const myRect = d3.select(rectRef.current);
        myRect.attr("width", 0).attr("height", 0);
    };

    const handleZoom = useCallback((e: d3.D3ZoomEvent<any, any>) => {
        d3.select(gZoomRef.current).attr("transform", e.transform.toString());
    }, []);

    const setupZoom = () => {
        const svg = d3.select<SVGSVGElement, unknown>(svgRef.current!);
        const gDrag = d3.select<SVGGElement, unknown>(gDragRef.current!);

        if (isMoveImg) {
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

    const getMappedLabel = (labelId: string) => {
        for (let i = 0; i < labelsMap.length; i++) {
            if (labelsMap[i][0] === labelId) {
                return labelsMap[i][1]
            }
        }
        return undefined
    }

    const bboxs = useMemo(() => {
        return idoc?.objects?.map((obj: DetectedObject, index: number) => {
            let tlx = (obj.tlx + borderDistWidth - 7) / widthRatio;
            let tly = (obj.tly + borderDistHeight - 5) / heightRatio;
            let brx = (obj.brx + borderDistWidth - 7) / widthRatio;
            let bry = (obj.bry + borderDistHeight - 5) / heightRatio;
            return (<g>
                <BoundingBox key={'bboxRect' + index} objIdx={index} opacity={0.5}
                             tlx={tlx} tly={tly} brx={brx} bry={bry}
                             onContextMenu={(e) => handleRightClick(e, obj)}/>
                <BBoxText
                    key={'bboxText' + index}
                    text={labelsMap ? getMappedLabel(obj.labelId)!.name : 'Placeholder'}
                    tlx={tlx} tly={tly} brx={brx} bry={bry}
                    onContextMenu={(e) => handleRightClick(e, obj)}
                    fontSize={Math.max(21, height / 30)}
                />
            </g>)
        })
    }, [idoc?.objects, showObjs])

    useEffect(() => {
        if (svgRef.current) {
            setupZoom();
        }
    }, [zoom, svgRef, handleZoom, isMoveImg]);

    return (
        <svg
            ref={svgRef}
            width="100%"
            height={pixelHeight + 'px'}
            style={{cursor: isMoveImg ? "auto" : "move"}}
        >
            <g ref={gZoomRef}>
                <g ref={gDragRef} style={{cursor: isMoveImg ? "crosshair" : "move"}}>
                    <image ref={imgRef} href={imgUrl} style={{outline: "1px solid black", height: imgHeight + 'px'}}
                           x={borderDistWidth} y={borderDistHeight}/>
                    <rect
                        ref={rectRef}
                        x={0} y={0} width={0} height={0}
                        stroke={"black"}
                        strokeWidth={3}
                        fill={"transparent"}
                    ></rect>
                </g>
                {showObjs && bboxs}
            </g>
        </svg>
    );
}

export default ImageAnnotator;