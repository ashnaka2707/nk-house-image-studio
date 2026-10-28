
import streamlit as st
import pandas as pd
from PIL import Image
from io import BytesIO
import zipfile
from pathlib import Path

st.set_page_config(
    page_title="NK House | Image Studio",
    page_icon="🧵",
    layout="wide"
)

st.title("NK HOUSE")
st.subheader("Bulk Image Studio")
st.write("Manage product images and wholesale pricing in one place.")

markups = {
    "Kurtis": 20.0,
    "Suit Sets": 18.0,
    "Sarees": 15.0,
    "Other": 20.0,
}

st.sidebar.header("Pricing settings")
st.sidebar.caption("Example markups only. Update these to your actual rates.")

st.header("1. Upload product images")

files = st.file_uploader(
    "Select multiple product images",
    type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=True
)

if files:
    st.success(f"{len(files)} images uploaded.")

    st.header("2. Product details")
    records = []
    branded_images = []

    logo_path = Path(__file__).parent / "nk_logo.png.png"

    if logo_path.exists():
        logo = Image.open(logo_path).convert("RGBA")
    else:
        logo = None
        st.warning(
            "Logo file not found. Make sure nk_logo.png.png "
            "is in the same folder as app.py."
        )

    position = st.selectbox(
        "Logo position",
        ["Bottom right", "Bottom left", "Top right", "Top left"]
    )

    logo_size = st.slider("Logo size (%)", 5, 25, 12)
    opacity = st.slider("Logo opacity (%)", 20, 100, 85)

    for i, file in enumerate(files):
        with st.expander(file.name, expanded=(i == 0)):
            image = Image.open(file).convert("RGB")
            st.image(image, caption="Original image", width=300)

            category = st.selectbox(
                "Product category",
                list(markups.keys()),
                key=f"category_{i}"
            )

            cost = st.number_input(
                "Supplier cost (₹)",
                min_value=0.0,
                value=0.0,
                step=10.0,
                key=f"cost_{i}"
            )

            markup = st.number_input(
                "Markup (%)",
                min_value=0.0,
                max_value=500.0,
                value=markups[category],
                step=1.0,
                key=f"markup_{i}"
            )

            price = round(cost * (1 + markup / 100), 2)
            st.write(f"**Calculated wholesale price: ₹{price:,.2f}**")

            records.append({
                "Filename": file.name,
                "Category": category,
                "Supplier Cost (₹)": cost,
                "Markup (%)": markup,
                "Wholesale Price (₹)": price,
            })

            branded = image.convert("RGBA")

            if logo is not None:
                logo_copy = logo.copy()

                target_width = max(1, int(image.width * logo_size / 100))
                target_height = max(
                    1,
                    int(logo.height * target_width / logo.width)
                )
                logo_copy = logo_copy.resize(
                    (target_width, target_height),
                    Image.Resampling.LANCZOS
                )

                alpha = logo_copy.getchannel("A")
                alpha = alpha.point(lambda value: int(value * opacity / 100))
                logo_copy.putalpha(alpha)

                margin = max(10, int(image.width * 0.02))

                if position == "Bottom right":
                    x = image.width - target_width - margin
                    y = image.height - target_height - margin
                elif position == "Bottom left":
                    x = margin
                    y = image.height - target_height - margin
                elif position == "Top right":
                    x = image.width - target_width - margin
                    y = margin
                else:
                    x = margin
                    y = margin

                branded.alpha_composite(logo_copy, (x, y))

                st.image(
                    branded.convert("RGB"),
                    caption="Preview with NK HOUSE logo",
                    width=300
                )

            output_image = BytesIO()
            branded.convert("RGB").save(output_image, format="JPEG", quality=95)
            branded_images.append(
                (f"NK_HOUSE_{Path(file.name).stem}.jpg", output_image.getvalue())
            )

    st.header("3. Review pricing")

    df = pd.DataFrame(records)
    st.dataframe(df, width="stretch")

    st.download_button(
        "Download pricing spreadsheet (CSV)",
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name="nk_house_pricing.csv",
        mime="text/csv"
    )

    st.header("4. Download branded images")

    if st.button("Prepare branded image ZIP"):
        output = BytesIO()

        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for filename, image_bytes in branded_images:
                archive.writestr(filename, image_bytes)

        st.download_button(
            "Download NK HOUSE branded images",
            data=output.getvalue(),
            file_name="nk_house_branded_images.zip",
            mime="application/zip"
        )

else:
    st.info("Upload product images to get started.")
