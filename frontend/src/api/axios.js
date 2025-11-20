import axios from "axios";

export default axios.create({
  baseURL: "https://medicreminder-production-aaca.up.railway.app/api",
  withCredentials: true,
});
