import React, { useState } from 'react';
import { useHistory } from 'react-router';
import ReactDOM from "react-dom";
const Login = () => {
//   const history = useHistory();
//   const [formState, setFormState] = useState({
//     login: true,
//     email: '',
//     password: '',
//     name: ''
//   });
const [token, setToken] = useState();
  return (
    <form>
      <label>
        <p>Username</p>
        <input type="text" />
      </label>
      <label>
        <p>Password</p>
        <input type="password" />
      </label>
      <div>
        <button type="submit">Submit</button>
      </div>
    </form>
  )
}

export default Login;