
import streamlit as st
import pandas as pd
from PIL import Image, ImageOps, UnidentifiedImageError
from io import BytesIO
import zipfile
from pathlib import Path
import gc

st.set_page_config(
    page_title="NK House | Image Studio",
    page_icon="🧵",
    layout="wide"
)

st.title("NK HOUSE")
st.subheader("Bulk Image Studio")
st.write("Prepare garment photos for retailer sharing.")

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
    "Select up to 500 product images",
    type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=True
)

if files:
    if len(files) > 500:
        st.error("Please upload no more than 500 images in one batch.")
        st.stop()

    st.success(f"{len(files)} images selected.")

    st.header("2. Batch settings")

    position = st.selectbox(
        "Logo position",
        ["Bottom right", "Bottom left", "Top right", "Top left"]
    )
    logo_size = st.slider("Logo size (%)", 5, 25, 12)
    opacity = st.slider("Logo opacity (%)", 20, 100, 85)

    preview_count = st.selectbox(
        "Number of images to preview",
        [5, 10, 20, 50],
        index=0
    )

    st.caption(
        "To keep large batches responsive, only a limited number of "
        "previews will be shown. All valid images will still be processed."
    )

    logo_path = Path(__file__).parent / "nk_logo.png.png"

    try:
        logo = Image.open(logo_path).convert("RGBA")
    except (FileNotFoundError, UnidentifiedImageError, OSError):
        logo = None
        st.error(
            "NK HOUSE logo not found or unreadable. "
            "Check that nk_logo.png.png is beside app.py."
        )
        st.stop()

    st.header("3. Process batch")

    if st.button("Process images", type="primary"):
        records = []
        failures = []
        output = BytesIO()
        progress = st.progress(0, text="Starting batch...")
        status = st.empty()

        used_names = set()
        processed = 0

        with zipfile.ZipFile(
            output, "w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            for i, file in enumerate(files):
                status.write(f"Processing {i + 1} of {len(files)}: {file.name}")

                try:
                    file.seek(0)
                    with Image.open(file) as opened:
                        image = ImageOps.exif_transpose(opened).convert("RGB")

                    branded = image.convert("RGBA")
                    target_width = max(1, int(image.width * logo_size / 100))
                    target_height = max(
                        1, int(logo.height * target_width / logo.width)
                    )
                    logo_copy = logo.resize(
                        (target_width, target_height),
                        Image.Resampling.LANCZOS
                    )

                    alpha = logo_copy.getchannel("A")
                    alpha = alpha.point(
                        lambda value: int(value * opacity / 100)
                    )
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

                    x = max(0, min(x, image.width - target_width))
                    y = max(0, min(y, image.height - target_height))
                    branded.alpha_composite(logo_copy, (x, y))

                    image_number = 1
                    base_name = Path(file.name).stem
                    output_name = f"NK_HOUSE_{base_name}.jpg"

                    while output_name.lower() in used_names:
                        image_number += 1
                        output_name = (
                            f"NK_HOUSE_{base_name}_{image_number}.jpg"
                        )

                    used_names.add(output_name.lower())

                    image_buffer = BytesIO()
                    branded.convert("RGB").save(
                        image_buffer, format="JPEG", quality=90, optimize=True
                    )
                    image_bytes = image_buffer.getvalue()
                    archive.writestr(output_name, image_bytes)

                    records.append({
                        "Original filename": file.name,
                        "Output filename": output_name,
                        "Status": "Success",
                        "Original size (KB)": round(
                            len(file.getvalue()) / 1024, 1
                        ),
                        "Output size (KB)": round(
                            len(image_bytes) / 1024, 1
                        ),
                    })

                    if processed < preview_count:
                        st.image(
                            image_bytes,
                            caption=f"Preview: {output_name}",
                            width=240
                        )

                    processed += 1
                    del image, branded, image_buffer, image_bytes
                    gc.collect()

                except (UnidentifiedImageError, OSError, ValueError) as exc:
                    failures.append({
                        "Filename": file.name,
                        "Reason": str(exc)[:200]
                    })

                progress.progress(
                    (i + 1) / len(files),
                    text=f"Completed {i + 1} of {len(files)}"
                )

        status.empty()
        progress.empty()

        st.session_state["batch_zip"] = output.getvalue()
        st.session_state["batch_records"] = records
        st.session_state["batch_failures"] = failures

        st.success(
            f"Batch complete: {len(records)} processed, "
            f"{len(failures)} failed."
        )

    if "batch_zip" in st.session_state:
        st.header("4. Download results")

        st.download_button(
            "Download all branded images (ZIP)",
            data=st.session_state["batch_zip"],
            file_name="nk_house_branded_images.zip",
            mime="application/zip"
        )

        result_df = pd.DataFrame(st.session_state["batch_records"])
        st.dataframe(result_df, width="stretch")

        st.download_button(
            "Download processing report (CSV)",
            data=result_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="nk_house_processing_report.csv",
            mime="text/csv"
        )

        failures = st.session_state["batch_failures"]
        if failures:
            st.warning("Some files could not be processed.")
            st.dataframe(pd.DataFrame(failures), width="stretch")

else:
    st.info("Upload product images to get started.")
