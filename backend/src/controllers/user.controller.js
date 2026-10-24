import { User } from "../models/user.model.js";

const register = async (req, res) => {
  try {
    const { username, email, phone, password } = req.body;

    if (!username || !email || !phone || !password) {
      return res.status(400).json({ status: 400, message: "All fields are required" });
    }

    const existingUser = await User.findOne({ $or: [{ email }, { username }] });
    if (existingUser) {
      const field = existingUser.email === email ? "Email" : "Username";
      return res.status(400).json({ status: 400, message: `${field} already exists` });
    }

    const newUser = await User.create({ username, email, phone, password });
    const safeUser = newUser.toObject ? newUser.toObject() : { ...newUser._doc };
    delete safeUser.password;

    return res.status(201).json({
      status: 201,
      message: "User created successfully",
      user: safeUser,
    });
  } catch (error) {
    if (error.code === 11000) {
      return res.status(400).json({ status: 400, message: "Username or email already taken" });
    }
    return res.status(500).json({ status: 500, message: "Registration failed", error: error.message });
  }
};

const login = async (req, res) => {
  try {
    const { username, password } = req.body;
    if (!username || !password) {
      return res.status(400).json({ status: 400, message: "Username and password are required" });
    }

    const user = await User.findOne({ username });
    if (!user) {
      return res.status(400).json({ status: 400, message: "User not found" });
    }

    const isPasswordCorrect = await user.isPasswordCorrect(password);
    if (!isPasswordCorrect) {
      return res.status(400).json({ status: 400, message: "Invalid password" });
    }

    const token = await user.setUser();
    const isProd = process.env.NODE_ENV === "production";
    res.cookie("accessToken", token, {
      httpOnly: true,
      secure: isProd,
      sameSite: isProd ? "None" : "Lax",
      maxAge: 24 * 60 * 60 * 1000,
    });

    const safeUser = user.toObject ? user.toObject() : { ...user._doc };
    if (safeUser && safeUser.password !== undefined) delete safeUser.password;

    return res.status(200).json({
      status: 200,
      message: "User logged in successfully",
      user: safeUser,
      token,
    });
  } catch (error) {
    return res.status(500).json({ status: 500, message: "Login failed", error: error.message });
  }
};

const getCurrentUser = async (req, res) => {
  try {
    const user = await User.findById(req.user._id).select("-password");
    if (!user) {
      return res.status(404).json({ status: 404, message: "User not found" });
    }
    res.json({
      status: 200,
      message: "User retrieved successfully",
      data: user,
    });
  } catch (error) {
    res.status(500).json({
      status: 500,
      message: "Internal server error",
      error: error.message,
    });
  }
};

const logout = async (req, res) => {
  res.clearCookie("accessToken",{
        httpOnly: true,
        secure: process.env.NODE_ENV==="production",
        sameSite: process.env.NODE_ENV==="production"?"None":"Lax",
  });
  res.json({ status: 200, message: "User logged out successfully" });
};

export { register, login, getCurrentUser, logout };