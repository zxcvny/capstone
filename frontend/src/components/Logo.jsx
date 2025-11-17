import { Link } from "react-router-dom"
import logo from "../assets/logo.png"
import logoMini from "../assets/logo-mini.png"

function Logo({ v = "default" }) {
    const logoSrc = v === "mini" ? logoMini : logo
    return(
        <Link to="/">
            <img src={logoSrc} alt="Zero to Mars Logo" />
        </Link>
    )
}
export default Logo;