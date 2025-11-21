import jwt from "jsonwebtoken";

const JWT_SECRET = process.env.ACCESS_TOKEN_SECRET || "dev-secret";

const authenticate=async(req,res,next)=>{
    const authHeader = req.headers.authorization;
    const tokenFromHeader = authHeader?.startsWith("Bearer ")
        ? authHeader.split(" ")[1]
        : null;
    const token= tokenFromHeader || req.cookies?.accessToken;
    if (!token) {
        return res.status(400).json({ status: 400,message: "Token Not Found" });
    }

    try {
        const user=jwt.verify(token,JWT_SECRET);
        req.user=user;
        return next();
    } catch (err) {
        return res.status(401).json({ status: 401,message: "Invalid Token" });
    }
};

export { authenticate }