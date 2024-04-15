import * as d3 from "d3";
import {ZoomBehavior} from "d3";
import {FC, Fragment, RefObject, useCallback, useEffect, useMemo, useRef} from "react";
import {useDispatch, useSelector} from "react-redux";
import BoundingBox from "../object_annotator/image_labeling/BBox";
import BBoxText from "../object_annotator/image_labeling/BBoxText";
import {BoundingBoxCoords, VisualFeature} from "../api/models/feature";
import {DetectedObject} from "../api/models/object";
import {clearFeatureBbox, setCurrBbox} from "../reducers/featureSlice";
import {CONCEPT_COLORS} from "../annotation_manager/AnnotationView";
import {ReactJSXElement} from "@emotion/react/types/jsx-namespace";


interface FeatureAnnotatorProps {
    objImgUrl: string;
    svgRef: RefObject<SVGSVGElement>;
    rectRef: RefObject<SVGRectElement>;
    zoom: ZoomBehavior<SVGSVGElement, unknown>;
    resetRect: Function;
    height: number;
}

const FeatureAnnotator: FC<FeatureAnnotatorProps> = ({
                                                         objImgUrl, svgRef, rectRef,
                                                         zoom, resetRect, height
                                                     }) => {
    const gZoomRef = useRef<SVGGElement>(null);
    const gDragRef = useRef<SVGGElement>(null);
    const imgRef = useRef<SVGImageElement>(null);

    // global state (redux)
    const dispatch = useDispatch();
    const detObj: DetectedObject | undefined = useSelector((state: any) => state.object.detObj);
    const feature: VisualFeature | undefined = useSelector((state: any) => state.feature.visualFeature);
    const conceptIdx: number | undefined = useSelector((state: any) => state.feature.conceptIdx);
    const prevBboxs: BoundingBoxCoords[] = useSelector((state: any) => state.feature.bboxs);
    const bboxsVis: boolean[] = useSelector((state: any) => state.feature.bboxsVis);
    const showPrevBboxs: boolean = useSelector((state: any) => state.feature.showPrevInput);
    const isMoveImg: boolean = useSelector((state: any) => state.feature.isMoveObjImg);

    let origWidth = detObj ? detObj.brx - detObj.tlx : 1
    let origHeight = detObj ? detObj.bry - detObj.tly : 1
    let pixelHeight = Math.max(500, height)
    let pixelWidth: number = svgRef.current ? svgRef.current.width.baseVal.value : 1
    let imgRatio = origWidth / origHeight
    let imgHeight = Math.max(500, height - (height / 10))
    let imgWidth = imgRatio * imgHeight
    let borderDistHeight = (pixelHeight - imgHeight) / 2
    let borderDistWidth: number = (pixelWidth / 2) - (imgWidth / 2)
    let widthRatio = origWidth / (pixelWidth - 2 * borderDistWidth)
    let heightRatio = origHeight / (pixelHeight - 2 * borderDistHeight)

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
        if (detObj && width > 10 && height > 10) {
            // pixelWidth = 2 * borderDistWidth
            const left = parseInt(myRect.attr("x")) - borderDistWidth;
            const top = parseInt(myRect.attr("y")) - borderDistHeight;
            // map screen coordinates to the original image pixels
            let mappedLeft = Math.floor(Math.max(0, left * widthRatio));
            let mappedTop = Math.floor(Math.max(0, top * heightRatio));
            let mappedRight = Math.ceil(Math.min(origWidth, mappedLeft + (width * widthRatio)));
            let mappedBottom = Math.ceil(Math.min(origHeight, mappedTop + (height * heightRatio)));
            const bbox_repr: BoundingBoxCoords = {
                tlx: mappedLeft, tly: mappedTop,
                brx: mappedRight, bry: mappedBottom,
            };
            dispatch(setCurrBbox(bbox_repr))
        } else {
            dispatch(clearFeatureBbox())
            resetRect();
        }
    };

    const handleZoom = useCallback((e: d3.D3ZoomEvent<any, any>) => {
        d3.select(gZoomRef.current).attr("transform", e.transform.toString());
    }, []);

    const setupZoom = () => {
        const svg = d3.select<SVGSVGElement, unknown>(svgRef.current!);
        const gDrag = d3.select<SVGGElement, unknown>(gDragRef.current!);

        if (isMoveImg) {
            gDrag.on(".drag", null);

            zoom.scaleExtent([0.1, 20]).on("zoom", handleZoom);
            svg.call(zoom);
        } else {
            svg.on(".zoom", null);

            drag.on("start", handleDragStart);
            drag.on("drag", handleDrag);
            drag.on("end", handleDragEnd);
            gDrag.call(drag);
        }
    };

    const createPrevBBoxElement = (bbox: BoundingBoxCoords, index: number) => {
        if (bboxsVis[index]) {
            let tlx = (bbox.tlx / widthRatio) + borderDistWidth;
            let tly = (bbox.tly / heightRatio) + borderDistHeight;
            let brx = (bbox.brx / widthRatio) + borderDistWidth;
            let bry = (bbox.bry / heightRatio) + borderDistHeight;
            return (<g key={'annoBbox' + index}>
                <BoundingBox key={'bboxRect' + index} objIdx={index} opacity={0.3}
                             color={'yellow'} tlx={tlx} tly={tly} brx={brx} bry={bry}/>
            </g>)
        }
        return <Fragment key={'bboxPlaceholder' + index}></Fragment>
    }

    const createFeatureBBoxElement = (bbox: BoundingBoxCoords, index: number, conceptIdx: number) => {
        if (bboxsVis[index]) {
            let tlx = (bbox.tlx / widthRatio) + borderDistWidth;
            let tly = (bbox.tly / heightRatio) + borderDistHeight;
            let brx = (bbox.brx / widthRatio) + borderDistWidth;
            let bry = (bbox.bry / heightRatio) + borderDistHeight;
            return (<g key={'featBbox' + index}>
                <BoundingBox key={'fbboxRect' + index} objIdx={index} opacity={0.3}
                             color={CONCEPT_COLORS[conceptIdx]}
                             tlx={tlx} tly={tly} brx={brx} bry={bry}/>
                <BBoxText
                    key={'fbboxText' + index}
                    text={(index + 1).toString()}
                    tlx={tlx} tly={tly} brx={brx} bry={bry}
                    fontSize={Math.max(21, height / 30)}
                />
            </g>)
        }
        return <Fragment key={'featPlaceholder' + index}></Fragment>
    }

    const bboxs = useMemo(() => {
        if (pixelWidth !== 0 && showPrevBboxs && conceptIdx !== undefined) {
            let featListLen = feature?.bboxs!.length
            if (featListLen) {
                let bboxList: ReactJSXElement[];
                bboxList = feature!.bboxs!.map((bbox: BoundingBoxCoords, index: number) =>
                    createFeatureBBoxElement(bbox, index, conceptIdx))
                if (prevBboxs.length > 0) {
                    bboxList.concat(prevBboxs.map((bbox: BoundingBoxCoords, index: number) =>
                        createPrevBBoxElement(bbox, featListLen! + index)))
                }
                return bboxList
            } else {
                return prevBboxs.map((bbox: BoundingBoxCoords, index: number) =>
                    createPrevBBoxElement(bbox, index))
            }
        }
        return <></>
    }, [feature?.bboxs, prevBboxs, showPrevBboxs, bboxsVis, pixelWidth])

    useEffect(() => {
        if (svgRef.current) {
            setupZoom();
        }
    }, [objImgUrl, zoom, svgRef.current, handleZoom, isMoveImg]);

    return (
        <svg
            ref={svgRef} width="100%" height={pixelHeight + 'px'}
            style={{cursor: isMoveImg ? "move" : "auto"}}
        >
            <g ref={gZoomRef}>
                <g ref={gDragRef} style={{cursor: isMoveImg ? "move" : "crosshair"}}>
                    <image ref={imgRef} href={objImgUrl} style={{outline: "1px solid black", height: imgHeight + 'px'}}
                           x={borderDistWidth} y={borderDistHeight}/>
                    <rect
                        ref={rectRef}
                        x={0} y={0} width={0} height={0}
                        stroke={"black"}
                        strokeWidth={3}
                        fill={"transparent"}
                    ></rect>
                </g>
                {bboxs}
            </g>
        </svg>
    );
}

export default FeatureAnnotator;