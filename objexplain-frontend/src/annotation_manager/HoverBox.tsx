import {FC, useState} from "react";


interface HoverBoxProps {
    word: any
    annotation: any
    conceptIdx: number
    hovertoggle: boolean
    color?: string
}

interface HighlightProps {
    text: string
    color?: string
}

export const Highlighted: FC<HighlightProps> = ({text, color = 'deepskyblue'}) => {
    return <span style={{backgroundColor: color}}>{text}</span>
};

const HoverBox: FC<HoverBoxProps> = ({word, annotation, conceptIdx, hovertoggle, color}) => {

    const hoverStyle = {
        position: 'absolute',
        display: 'inline-block',
        height: '22px',
        width: 'fit-content',
        overflow: 'nowrap',
        textOverflow: 'nowrap',
        whitespace: 'nowrap',
        alignCenter: 'float',
        marginTop: '-30px',
        float: 'center',
        marginLeft: '-75px',
        borderRadius: '25px',
        backgroundColor: color,
        fontSize: '12pt',
        zIndex: '100',
        boxShadow: '1px 1px 5px',
        paddingRight: '5px',
        paddingLeft: '5px',
    }

    const [hover, setHover] = useState(false)

    const normalStyle = {
        display: 'none'
    }

    const onMouseEnter = (e: any) => {
        if (hovertoggle) {
            setHover(true)
        }
    }

    const onMouseLeave = () => {
        setHover(false)
    }

    return (
        <>
            <a style={hover ? hoverStyle : normalStyle}>Marked
                Concept: {conceptIdx} Author: {annotation.autoCreated ? "Machine" : "User"}</a>
            <a style={{fontSize: '1em', color: 'none', padding: '0px 2px 0px 2px', marginTop: '6px', zIndex: '1'}}
               onMouseEnter={onMouseEnter} onMouseLeave={onMouseLeave}>
                <Highlighted text={word} color={color}/></a>
        </>
    )
}
export default HoverBox;
