import "./button.scss";
import PropTypes from "prop-types"

function Button({ disabled, onClick, text, emoji }) {
  return (
    <button className="button" disabled={disabled} onClick={onClick}>
      <span>{emoji}</span>
      <span>{text}</span>
    </button>
  );
}

Button.propTypes = {
  disabled: PropTypes.bool.isRequired,
  onClick: PropTypes.func.isRequired,
  text: PropTypes.string.isRequired,
  emoji: PropTypes.string.isRequired,
}

export default Button;
