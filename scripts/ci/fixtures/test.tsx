interface Props {
  name: string;
}
function Greeting(props: Props) {
  return <div className="greet">Hello {props.name}</div>;
}
